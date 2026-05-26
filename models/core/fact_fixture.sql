-- Model: fact_fixture
-- Grain: 1 row per fixture (fixture_id)
-- Materialization: table (football_core) — physical table for match-level context at fixture grain
-- Sources:
--   int_fixture_spine — primary; denormalised fixture, scores, season dates, and coverage flags
-- Purpose:
--   Core fact for one row per match. Competition, timing, teams, venue, scores, and API coverage
--   flags for the league-season. Consumption layer should join here — not int_fixture_spine.
--   Join dim_league on league_id; dim_club on home_team_id or away_team_id; dim_venue on venue_id.
-- Competitions:
--   All 15 tracked league_ids — filter downstream for league / cup / tournament scope.
-- Output columns (from int_fixture_spine):
--   fixture_id, league_id, league_name, league_country, league_season
--   season_start_date, season_end_date, is_current_season, league_round
--   match_date, match_timestamp, first_half_start, second_half_start
--   elapsed_minutes, extra_time, match_duration, match_status_short, match_status_long
--   match_referee, timezone
--   home_team_id, home_team_name, is_home_team_winner, away_team_id, away_team_name, is_away_team_winner
--   venue_id, venue_name, venue_city
--   halftime_home_team_score, halftime_away_team_score, fulltime_home_team_score, fulltime_away_team_score
--   extratime_home_team_score, extratime_away_team_score, penalty_home_team_score, penalty_away_team_score
--   has_fixtures_events_coverage, has_fixtures_lineups_coverage, has_standings_coverage
--   has_players_coverage, has_topscorers_coverage, has_injuries_coverage
--   has_predictions_coverage, has_odds_coverage, ingested_at
-- Excludes:
--   Club perspective (goals_scored per team) — use fact_club_match_stats (two rows per fixture)
--   In-match events — use fact_fixture_events
--   Season aggregates — use fact_club_season or fact_standings
-- Design notes:
--   Thin exposure layer: match_duration and score joins live in int_fixture_spine.
--   is_home_team_winner / is_away_team_winner are null on draws and before kick-off.
--   match_status_short: FT = full time, AET = after extra time, PEN = penalty shootout outcome.
--   Coverage flags describe what the API supports for that league-season, not what was ingested.
-- Consumers (consumption layer):
--   fact_fixture_events, fact_club_match_stats, fact_player_match_stats (join on fixture_id),
--   mart_league_week, marts, Streamlit match explorer

{{ config(materialized='table') }}

select
    -- identifiers
    fixture_id,
    league_id,
    -- competition and season
    league_name,
    league_country,
    league_season,
    season_start_date,
    season_end_date,
    is_current_season,
    league_round,
    -- match timing and status
    match_date,
    match_timestamp,
    first_half_start,
    second_half_start,
    elapsed_minutes,
    extra_time,
    match_duration,
    match_status_short,
    match_status_long,
    match_referee,
    timezone,
    -- teams
    home_team_id,
    home_team_name,
    is_home_team_winner,
    away_team_id,
    away_team_name,
    is_away_team_winner,
    -- venue
    venue_id,
    venue_name,
    venue_city,
    -- scores
    halftime_home_team_score,
    halftime_away_team_score,
    fulltime_home_team_score,
    fulltime_away_team_score,
    extratime_home_team_score,
    extratime_away_team_score,
    penalty_home_team_score,
    penalty_away_team_score,
    -- coverage flags
    has_fixtures_events_coverage,
    has_fixtures_lineups_coverage,
    has_standings_coverage,
    has_players_coverage,
    has_topscorers_coverage,
    has_injuries_coverage,
    has_predictions_coverage,
    has_odds_coverage,
    -- metadata
    ingested_at
from {{ ref('int_fixture_spine') }}
