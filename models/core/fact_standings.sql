-- Model: fact_standings
-- Grain: 1 row per team per league per season per group (league_id, league_season, team_id, group_name)
-- Materialization: table (football_core) — physical table for league table snapshots
-- Sources:
--   int_standings — primary; latest standings snapshot with win_rate and points_per_game
-- Purpose:
--   Core fact for current league position and table stats. Reflects the most recent API standings
--   ingest — not a matchday-by-matchday history. Join dim_club on team_id and dim_league on league_id.
--   Join fact_fixture only for match-level analysis; standings are not keyed by fixture_id.
-- Output columns (from int_standings):
--   league_id, league_name, league_season, team_id, team_name, group_name
--   team_rank, team_points, matches_played, matches_won, matches_drawn, matches_lost
--   goals_for, goals_against, goals_difference
--   home_matches_played, home_matches_won, home_matches_drawn, home_matches_lost
--   home_goals_for, home_goals_against
--   away_matches_played, away_matches_won, away_matches_drawn, away_matches_lost
--   away_goals_for, away_goals_against
--   win_rate, points_per_game, form, standing_status, standing_description
--   last_updated, ingested_at
-- Excludes:
--   Match-level results — use fact_fixture or fact_club_match_stats
--   Historical table positions by round — not available in source data
-- Design notes:
--   Thin exposure layer: win_rate and points_per_game derived in int_standings.
--   group_name distinguishes World Cup / UCL groups; may be empty for single-table leagues.
--   Used as left-join context on int_club_intl_runs / int_national_team_runs at intermediate only;
--   consumption layer should use this fact for table views, not int_standings.
-- Consumers (consumption layer):
--   mart_league_standings, Streamlit standings page, promotion/relegation analysis

{{ config(materialized='table') }}

select
    -- identifiers
    league_id,
    league_season,
    team_id,
    group_name,
    -- competition and team
    league_name,
    team_name,
    -- standing position
    team_rank,
    team_points,
    -- overall record
    matches_played,
    matches_won,
    matches_drawn,
    matches_lost,
    goals_for,
    goals_against,
    goals_difference,
    -- home record
    home_matches_played,
    home_matches_won,
    home_matches_drawn,
    home_matches_lost,
    home_goals_for,
    home_goals_against,
    -- away record
    away_matches_played,
    away_matches_won,
    away_matches_drawn,
    away_matches_lost,
    away_goals_for,
    away_goals_against,
    -- derived metrics
    win_rate,
    points_per_game,
    -- form and status
    form,
    standing_status,
    standing_description,
    -- metadata
    last_updated,
    ingested_at
from {{ ref('int_standings') }}
