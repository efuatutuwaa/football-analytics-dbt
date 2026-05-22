-- Model: int_fixture_spine
-- Grain: 1 row per fixture_id
-- Materialization: incremental (merge). unique_key: fixture_id. Incremental on stg_fixtures.ingested_at
-- Sources:
--   stg_fixtures — schedule, teams, venue, status, timing
--   stg_fixture_scores — left join; halftime / fulltime / extratime / penalty scores
--   stg_league_seasons — left join on league_id + league_season; season dates and coverage flags
-- Purpose:
--   Single denormalised match record for all downstream club and player intermediate models.
--   Centralises score columns and renames status fields to match_status_* for consistency.
-- Derived fields:
--   match_duration = elapsed_minutes + coalesce(extra_time, 0)
--   is_home_team_winner / is_away_team_winner from staging (null on draws and before kick-off)
-- Coverage flags (from league_seasons):
--   has_fixtures_events_coverage, has_fixtures_lineups_coverage, has_standings_coverage,
--   has_players_coverage, has_topscorers_coverage, has_injuries_coverage,
--   has_predictions_coverage, has_odds_coverage
-- Downstream:
--   Intermediate: int_club_matchday_metrics, int_club_domestic_cup_runs, int_club_intl_runs,
--   int_national_team_runs, int_player_match_stats
--   Core (consumption): fact_fixture — marts and BI should join fact_fixture, not this model
-- Notes: Parent of the intermediate layer — run order should build this before dependents.

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
