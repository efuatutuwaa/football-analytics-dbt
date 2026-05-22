-- Model: int_club_intl_runs
-- Grain: 1 row per club per fixture (fixture_id, team_id, league_id, league_season, league_round)
-- Materialization: table (full refresh) — required so is_farthest_round sees the full season partition
-- Sources:
--   int_fixture_spine — league_id in (2, 15)
--   stg_teams — inner join; clubs only
--   stg_standings — left join on league_id + league_season + team_id for group-stage snapshot fields
-- Competitions (league_id):
--   2 UEFA Champions League, 15 FIFA Club World Cup
-- Purpose:
--   Club perspective on European / global tournament matches with group-stage context where available.
--   Two rows per fixture. is_home and perspective scores included (unlike national team runs).
-- Business logic:
--   round_order — group and knockout rounds mapped to numeric ranks
--   is_farthest_round — true on every match in deepest round (group or knockout), not exit-only
--   Group columns (group_name, group_points, etc.) from standings — null in knockout-only rows
--   Dedup: qualify on fixture_id, team_id, league_id, league_season, league_round
-- Downstream:
--   fact_club_intl_run, mart_club_european_performance
-- Notes:
--   Club World Cup format changed in 2025 (7-team → 32-team) — compare seasons cautiously.
--   UCL always has group stage in scope; CWC group stage mainly from 2025 edition onward.
-- Excludes: domestic leagues, domestic cups, national teams

{{ config(materialized='table') }}

with fixtures as (
    select * from {{ ref('int_fixture_spine') }}
    where league_id in (2, 15) -- filter club international competitions
),

teams as (
    select * from {{ ref('stg_teams') }}
    where is_national_team = false -- filter to club teams only
),

standings as (
    select * from {{ ref('stg_standings') }}
    where league_id in (2, 15) -- UCL (2) always has group stage; CWC (15) from 2025 onwards
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
        -- group stage record (where applicable)
        s.group_name,
        s.team_rank as group_position,
        s.team_points as group_points,
        s.matches_won as group_wins,
        s.matches_drawn as group_draws,
        s.matches_lost as group_losses,
        s.goals_for as group_goals_for,
        s.goals_against as group_goals_against,
        s.goals_difference as group_goal_difference,
        -- metadata
        f.ingested_at
    from fixtures as f
    inner join teams as t on f.home_team_id = t.team_id
    left join standings as s
        on
            f.league_id = s.league_id
            and f.league_season = s.league_season
            and f.home_team_id = s.team_id

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
        -- group stage record (where applicable)
        s.group_name,
        s.team_rank as group_position,
        s.team_points as group_points,
        s.matches_won as group_wins,
        s.matches_drawn as group_draws,
        s.matches_lost as group_losses,
        s.goals_for as group_goals_for,
        s.goals_against as group_goals_against,
        s.goals_difference as group_goal_difference,
        -- metadata
        f.ingested_at
    from fixtures as f
    inner join teams as t on f.away_team_id = t.team_id
    left join standings as s
        on
            f.league_id = s.league_id
            and f.league_season = s.league_season
            and f.away_team_id = s.team_id
),

round_ordered as (

    select
        *,
        case
            when league_round like 'Group %' then 30
            when league_round like 'League Stage%' then 30
            when league_round like 'Group Stage%' then 30
            when league_round like 'Preliminary%' then 5
            when league_round = '1st Qualifying Round' then 10
            when league_round = '2nd Qualifying Round' then 15
            when league_round = '3rd Qualifying Round' then 20
            when league_round = 'Play-offs' then 25
            when league_round = '1st Round' then 25
            when league_round = '2nd Round' then 35
            when league_round = 'Knockout Round Play-offs' then 35
            when league_round = 'Round of 32' then 40
            when league_round = 'Round of 16' then 50
            when league_round = '8th Finals' then 50
            when league_round = '5th Place Final' then 55
            when league_round = 'Quarter-finals' then 60
            when league_round = '3rd Place Final' then 65
            when league_round = 'Semi-finals' then 70
            when league_round = 'Final' then 100
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
    group_name,
    group_position,
    group_points,
    group_wins,
    group_draws,
    group_losses,
    group_goals_for,
    group_goals_against,
    group_goal_difference,
    ingested_at
from round_ordered
