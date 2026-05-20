-- Model: int_fixture_spine
-- Grain: 1 row per fixture_id
-- Materialization: incremental (merge) — new fixtures are added nightly as they are scheduled
-- Sources: stg_fixtures (primary), stg_fixture_scores (left joined on fixture_id for
--          halftime/fulltime/extratime/penalty scores), stg_league_seasons (left joined on
--          league_id + season_year for season dates and coverage flags)
-- Purpose:
--   Denormalized fixture record covering all competitions and seasons. Derives match_date,
--   match_duration (elapsed + coalesce(extra_time, 0)), is_home_team_winner, and
--   is_away_team_winner. Carries halftime, fulltime, extratime, and penalty scores alongside
--   league coverage flags (events, lineups, standings, players, topscorers, injuries,
--   predictions, odds). Serves as the join foundation for all club- and player-level
--   intermediate models.

{{ config(
    materialized='incremental',
    unique_key='fixture_id',
    incremental_strategy='merge'
) }}

with fixtures as (
    select * from {{ ref('stg_fixtures') }}
    {% if is_incremental() %}
        where ingested_at > (select max(ingested_at) from {{ this }})  -- noqa: RF02
    {% endif %}
),

scores as (
    select * from {{ ref('stg_fixture_scores') }}
),

league_seasons as (
    select * from {{ ref('stg_league_seasons') }}
)

select
    -- identifiers
    f.fixture_id,
    f.league_id,
    -- league and season context
    f.league_name,
    f.league_country,
    f.league_season,
    l.season_start_date,
    l.season_end_date,
    l.is_current_season,
    f.league_round,
    -- match timing
    f.match_date,
    f.match_timestamp,
    f.first_half_start,
    f.second_half_start,
    f.elapsed_minutes,
    f.extra_time,
    f.elapsed_minutes + coalesce(f.extra_time, 0) as match_duration,
    -- match status
    f.status_long as match_status_long,
    f.status_short as match_status_short,
    f.referee as match_referee,
    f.timezone,
    -- home team
    f.home_team_id,
    f.home_team_name,
    f.is_home_team_winner,
    -- away team
    f.away_team_id,
    f.away_team_name,
    f.is_away_team_winner,
    -- venue
    f.venue_id,
    f.venue_name,
    f.venue_city,
    -- scores
    s.halftime_home_team_score,
    s.halftime_away_team_score,
    s.fulltime_home_team_score,
    s.fulltime_away_team_score,
    s.extratime_home_team_score,
    s.extratime_away_team_score,
    s.penalty_home_team_score,
    s.penalty_away_team_score,
    -- coverage flags
    l.has_fixtures_events_coverage,
    l.has_fixtures_lineups_coverage,
    l.has_standings_coverage,
    l.has_players_coverage,
    l.has_topscorers_coverage,
    l.has_injuries_coverage,
    l.has_predictions_coverage,
    l.has_odds_coverage,
    -- metadata
    f.ingested_at

from fixtures as f
left join scores as s
    on f.fixture_id = s.fixture_id
left join league_seasons as l
    on
        f.league_id = l.league_id
        and f.league_season = l.season_year
