-- Model: mart_league_standings
-- Grain: 1 row per team per domestic league per season per group (league_id, league_season, team_id, group_name)
-- Materialization: table (football_marts) — reporting layer; join dim_club and dim_league in BI
-- Sources (consumption layer only — do not ref int_*):
--   fact_standings — primary; latest API snapshot per league season (not matchday history)
--   dim_club       — optional enrich on team_id
--   dim_league     — optional enrich on league_id
-- Purpose:
--   Current domestic league table for BI and Streamlit standings page: rank, points, form string,
--   home/away splits, promotion/relegation status. Point-in-time snapshot — re-ingest refreshes.
-- Competitions (league_id):
--   39 Premier League, 61 Ligue 1, 78 Bundesliga, 135 Serie A, 140 La Liga
-- Output columns:
--   Same as fact_standings for domestic leagues (see fact header for full column list)
-- Excludes:
--   World Cup / UCL group tables — use fact_standings directly or tournament marts
--   Match-level results — fact_club_match_stats
--   Season totals derived from fixtures — mart_club_season (may differ slightly from API snapshot)
-- SQL patterns: thin filter passthrough (pattern G-style filter, no aggregation)
-- Design notes:
--   group_name is usually empty for single-table domestic leagues; retained for grain parity with fact.
--   mart_club_honours uses fact_standings for league titles (team_rank = 1) — same underlying snapshot.
-- Consumers:
--   Streamlit standings page, promotion/relegation labels, join to mart_club_season for context

{{ config(materialized='table') }}

select
    league_id,
    league_name,
    league_season,
    team_id,
    team_name,
    group_name,
    team_rank,
    team_points,
    matches_played,
    matches_won,
    matches_drawn,
    matches_lost,
    goals_for,
    goals_against,
    goals_difference,
    home_matches_played,
    home_matches_won,
    home_matches_drawn,
    home_matches_lost,
    home_goals_for,
    home_goals_against,
    away_matches_played,
    away_matches_won,
    away_matches_drawn,
    away_matches_lost,
    away_goals_for,
    away_goals_against,
    win_rate,
    points_per_game,
    form,
    standing_status,
    standing_description,
    last_updated,
    ingested_at
from {{ ref('fact_standings') }}
where league_id in (39, 61, 78, 135, 140)
