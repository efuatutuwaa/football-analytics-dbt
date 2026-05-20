-- Model: int_club_domestic_cup_runs
-- Grain: 1 row per team_id, league_id (cup competition), league_season, league_round
-- Materialization: incremental (merge) — cup fixtures accumulate throughout the season
-- Sources: int_fixture_spine (primary), stg_teams (inner joined on team_id for team attributes)
-- Competitions: FA Cup (45), Carabao Cup (48), Coupe de France (66),
--               DFB-Pokal (81), Coppa Italia (137), Copa del Rey (143)
-- Purpose:
--   Tracks each club's progression through domestic cup competitions per season.
--   Captures round-by-round results and the farthest stage reached.
--   Designed to complement int_club_league_periods to support double/treble analysis.

{{ config(
    materialized='incremental',
    unique_key=['fixture_id', 'team_id', 'league_id', 'league_season', 'league_round'],
    incremental_strategy='merge'
) }}

with fixtures as (
    select * from {{ ref('int_fixture_spine') }}
    where
        league_id in (45, 48, 66, 81, 137, 143) -- filter to domestic cup competitions
    {% if is_incremental() %}
        and ingested_at > (select max(ingested_at) from {{ this }})  -- noqa: RF02
    {% endif %}
),

teams as (
    select * from {{ ref('stg_teams') }}
    where is_national_team = false -- filter to club teams only
),

cup_runs as (

    -- home team perspective
    select
        -- identifiers
        f.fixture_id,
        f.league_id,
        f.home_team_id as team_id,
        f.home_team_name as team_name,
        t.team_code,
        t.team_country,
        f.away_team_id as opponent_team_id,
        f.away_team_name as opponent_team_name,
        true as is_home,
        f.is_home_team_winner as is_winner,
        -- league and season context
        f.league_name,
        f.league_country,
        f.league_season,
        f.season_start_date,
        f.season_end_date,
        f.is_current_season,
        f.league_round,
        -- match timing
        f.match_date,
        f.match_timestamp,
        f.first_half_start,
        f.second_half_start,
        f.elapsed_minutes,
        f.extra_time,
        f.match_duration,
        -- match status
        f.match_status_long,
        f.match_status_short,
        f.match_referee,
        f.timezone,
        -- scores
        f.fulltime_home_team_score as goals_scored,
        f.fulltime_away_team_score as goals_conceded,
        f.halftime_home_team_score as team_halftime_score,
        f.halftime_away_team_score as opponent_halftime_score,
        f.extratime_home_team_score as team_extratime_score,
        f.extratime_away_team_score as opponent_extratime_score,
        f.penalty_home_team_score as team_penalty_score,
        f.penalty_away_team_score as opponent_penalty_score,
        -- metadata
        f.ingested_at
    from fixtures as f
    inner join teams as t on f.home_team_id = t.team_id

    union all

    -- away team perspective
    select
        -- identifiers
        f.fixture_id,
        f.league_id,
        f.away_team_id as team_id,
        f.away_team_name as team_name,
        t.team_code,
        t.team_country,
        f.home_team_id as opponent_team_id,
        f.home_team_name as opponent_team_name,
        false as is_home,
        f.is_away_team_winner as is_winner,
        -- league and season context
        f.league_name,
        f.league_country,
        f.league_season,
        f.season_start_date,
        f.season_end_date,
        f.is_current_season,
        f.league_round,
        -- match timing
        f.match_date,
        f.match_timestamp,
        f.first_half_start,
        f.second_half_start,
        f.elapsed_minutes,
        f.extra_time,
        f.match_duration,
        -- match status
        f.match_status_long,
        f.match_status_short,
        f.match_referee,
        f.timezone,
        -- scores
        f.fulltime_away_team_score as goals_scored,
        f.fulltime_home_team_score as goals_conceded,
        f.halftime_away_team_score as team_halftime_score,
        f.halftime_home_team_score as opponent_halftime_score,
        f.extratime_away_team_score as team_extratime_score,
        f.extratime_home_team_score as opponent_extratime_score,
        f.penalty_away_team_score as team_penalty_score,
        f.penalty_home_team_score as opponent_penalty_score,
        -- metadata
        f.ingested_at
    from fixtures as f
    inner join teams as t on f.away_team_id = t.team_id

),

round_ordered as (

    select
        *,
        case league_round
            when 'Final' then 100
            when 'Semi-finals' then 90
            when 'Quarter-finals' then 80
            when 'Round of 16' then 70
            when '8th Finals' then 70
            when 'Round of 32' then 60
            when 'Round of 64' then 50
            when 'Round of 128' then 40
            when '1/128-finals' then 40
            when '5th Round' then 35
            when '4th Round' then 34
            when '3rd Round' then 33
            when '7th Round' then 33
            when '8th Round' then 34
            when '2nd Round' then 32
            when '1st Round' then 31
            when 'Preliminary Round' then 20
            when 'Extra Preliminary Round' then 10
            else 0
        end as round_order
    from cup_runs

)

select
    fixture_id,
    league_id,
    team_id,
    team_name,
    team_code,
    team_country,
    opponent_team_id,
    opponent_team_name,
    is_home,
    is_winner,
    league_name,
    league_country,
    league_season,
    season_start_date,
    season_end_date,
    is_current_season,
    league_round,
    round_order,
    round_order = max(round_order) over (
        partition by team_id, league_id, league_season
    ) as is_farthest_round,
    match_date,
    match_timestamp,
    first_half_start,
    second_half_start,
    elapsed_minutes,
    extra_time,
    match_duration,
    match_status_long,
    match_status_short,
    match_referee,
    timezone,
    goals_scored,
    goals_conceded,
    team_halftime_score,
    opponent_halftime_score,
    team_extratime_score,
    opponent_extratime_score,
    team_penalty_score,
    opponent_penalty_score,
    ingested_at
from round_ordered
