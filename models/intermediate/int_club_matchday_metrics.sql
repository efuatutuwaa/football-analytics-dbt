-- Model: int_club_matchday_metrics
-- Grain: 1 row per team_id, fixture_id
-- Materialization: incremental (merge) — match results accumulate throughout the season
-- Sources: int_fixture_spine (primary), stg_teams (inner joined on team_id for team attributes),
--          stg_fixture_statistics (left joined on fixture_id + team_id for shots, possession, passes)
-- Competitions: all (league, domestic cup, international — filter downstream as needed)
-- Purpose:
--   Tracks per-match outcomes for each club across all competitions.
--   Captures goals scored/conceded, match result, clean sheets, home/away context,
--   and match statistics (shots, possession, corners, fouls, passes).
--   Designed to feed fact_club_match_stats and support rolling form analysis downstream.

{{ config(
    materialized='incremental',
    unique_key=['team_id', 'fixture_id'],
    incremental_strategy='merge'
) }}

with fixtures as (
    select * from {{ ref('int_fixture_spine') }}
    {% if is_incremental() %}
        where ingested_at > (select max(ingested_at) from {{ this }})  -- noqa: RF02
    {% endif %}
),

teams as (
    select * from {{ ref('stg_teams') }}
    where is_national_team = false -- filter to club teams only
),

fixture_stats as (
    select * from {{ ref('stg_fixture_statistics') }}
    {% if is_incremental() %}
        where ingested_at > (select max(ingested_at) from {{ this }})  -- noqa: RF02
    {% endif %}
),

matchday_metrics as (

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
        -- scores and outcomes
        f.fulltime_home_team_score as goals_scored,
        f.fulltime_away_team_score as goals_conceded,
        f.halftime_home_team_score as team_halftime_score,
        f.halftime_away_team_score as opponent_halftime_score,
        f.extratime_home_team_score as team_extratime_score,
        f.extratime_away_team_score as opponent_extratime_score,
        f.penalty_home_team_score as team_penalty_score,
        f.penalty_away_team_score as opponent_penalty_score,
        f.fulltime_home_team_score - f.fulltime_away_team_score as goal_difference,
        case
            when f.fulltime_home_team_score > f.fulltime_away_team_score then 'win'
            when f.fulltime_home_team_score < f.fulltime_away_team_score then 'loss'
            else 'draw'
        end as match_result,
        coalesce(f.fulltime_away_team_score = 0, false) as is_clean_sheet,
        -- match statistics (from fixture_stats)
        fs.shots_on_goal,
        fs.shots_off_goal,
        fs.total_shots,
        fs.blocked_shots,
        fs.shots_inside_box,
        fs.shots_outside_box,
        fs.fouls,
        fs.corner_kicks,
        fs.offsides,
        fs.ball_possession,
        fs.yellow_cards,
        fs.red_cards,
        fs.goalkeeper_saves,
        fs.total_passes,
        fs.accurate_passes,
        fs.pass_accuracy,
        -- metadata
        f.ingested_at
    from fixtures as f
    inner join teams as t on f.home_team_id = t.team_id
    left join fixture_stats as fs on f.fixture_id = fs.fixture_id and f.home_team_id = fs.team_id

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
        -- scores and outcomes
        f.fulltime_away_team_score as goals_scored,
        f.fulltime_home_team_score as goals_conceded,
        f.halftime_away_team_score as team_halftime_score,
        f.halftime_home_team_score as opponent_halftime_score,
        f.extratime_away_team_score as team_extratime_score,
        f.extratime_home_team_score as opponent_extratime_score,
        f.penalty_away_team_score as team_penalty_score,
        f.penalty_home_team_score as opponent_penalty_score,
        f.fulltime_away_team_score - f.fulltime_home_team_score as goal_difference,
        case
            when f.fulltime_away_team_score > f.fulltime_home_team_score then 'win'
            when f.fulltime_away_team_score < f.fulltime_home_team_score then 'loss'
            else 'draw'
        end as match_result,
        coalesce(f.fulltime_home_team_score = 0, false) as is_clean_sheet,
        -- match statistics (from fixture_stats)
        fs.shots_on_goal,
        fs.shots_off_goal,
        fs.total_shots,
        fs.blocked_shots,
        fs.shots_inside_box,
        fs.shots_outside_box,
        fs.fouls,
        fs.corner_kicks,
        fs.offsides,
        fs.ball_possession,
        fs.yellow_cards,
        fs.red_cards,
        fs.goalkeeper_saves,
        fs.total_passes,
        fs.accurate_passes,
        fs.pass_accuracy,
        -- metadata
        f.ingested_at
    from fixtures as f
    inner join teams as t on f.away_team_id = t.team_id
    left join fixture_stats as fs on f.fixture_id = fs.fixture_id and f.away_team_id = fs.team_id

)

select * from matchday_metrics
