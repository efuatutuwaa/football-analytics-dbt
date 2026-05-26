-- Model: fact_club_season
-- Grain: 1 row per club per domestic league per season (team_id, league_id, league_season)
-- Materialization: table (football_core) — physical table for league season summaries
-- Sources:
--   int_club_season_metrics — primary; season totals aggregated from finished league fixtures
-- Purpose:
--   Core fact for domestic league performance at season grain. One row per club per league
--   per season — wins, draws, losses, goals, goal difference, clean sheets. Metrics are
--   derived in dbt from int_club_matchday_metrics (not API /teams/statistics).
--   Join dim_club on team_id and dim_league on league_id in marts or BI.
-- Domestic leagues in scope (league_id):
--   39 Premier League, 61 Ligue 1, 78 Bundesliga, 135 Serie A, 140 La Liga
-- Output columns (from int_club_season_metrics):
--   team_id, team_name, league_id, league_name, league_season
--   matches_played, wins, draws, losses, goals_scored, goals_conceded, goal_difference, clean_sheets
-- Excludes:
--   Match-level detail — use fact_club_match_stats
--   Domestic cups — use fact_club_domestic_cup_run / mart_club_domestic_cup_performance
--   European club tournaments — use fact_club_intl_run
--   Cup or international fixtures in int_club_matchday_metrics — filtered out via int_club_league_periods
-- Design notes:
--   Thin exposure layer: aggregation and league-only filter live in intermediate.
--   matches_played counts finished league fixtures only (match_result not null in int_club_season_metrics).
--   Scheduled/postponed rows stay in int_club_matchday_metrics but are excluded from season totals.
--   Re-run int_club_matchday_metrics + int_club_season_metrics after ingest to refresh season totals.
-- Consumers (consumption layer):
--   mart_club_season, season-on-season analysis, double/treble with cup/intl marts

{{ config(materialized='table') }}

select
    -- identifiers
    team_id,
    league_id,
    league_season,
    -- club and competition
    team_name,
    league_name,
    -- season totals
    matches_played,
    wins,
    draws,
    losses,
    goals_scored,
    goals_conceded,
    goal_difference,
    clean_sheets
from {{ ref('int_club_season_metrics') }}
