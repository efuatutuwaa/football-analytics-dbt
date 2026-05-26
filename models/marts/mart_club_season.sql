-- Model: mart_club_season
-- Grain: 1 row per club per domestic league per season (team_id, league_id, league_season)
-- Materialization: table (football_marts) — reporting layer; join dim_club and dim_league in BI
-- Sources (consumption layer only — do not ref int_*):
--   fact_club_season — primary; thin enrich with derived league-table metrics
--   dim_club         — optional enrich on team_id
--   dim_league       — optional enrich on league_id
-- Purpose:
--   Domestic league season summary for club dashboards: W/D/L, goals, clean sheets, plus
--   points and rates for league-table style charts. Join mart_club_honours on team_id + league_season
--   for treble context; cup/European detail stays in sibling marts.
-- Competitions (league_id):
--   39 Premier League, 61 Ligue 1, 78 Bundesliga, 135 Serie A, 140 La Liga
-- Output columns:
--   team_id, team_name, league_id, league_name, league_season
--   matches_played, wins, draws, losses, goals_scored, goals_conceded, goal_difference, clean_sheets
--   league_points — wins * 3 + draws (3-1-0)
--   win_rate, points_per_game, goals_scored_per_match, goals_conceded_per_match
-- Excludes:
--   Domestic cups — mart_club_domestic_cup_performance
--   European club tournaments — mart_club_european_performance
--   Match-level rows — mart_club_matchday
-- SQL patterns: thin passthrough + derived metrics (no A/B/C aggregation here)
-- Design notes:
--   Season totals are computed upstream in int_club_season_metrics; this mart only adds
--   BI-friendly rates. matches_played = wins + draws + losses (finished fixtures only upstream).
-- Consumers:
--   Streamlit club season page, season-on-season comparisons, portfolio league section

{{ config(materialized='table') }}

select
    team_id,
    team_name,
    league_id,
    league_name,
    league_season,
    matches_played,
    wins,
    draws,
    losses,
    goals_scored,
    goals_conceded,
    goal_difference,
    clean_sheets,
    wins * 3 + draws as league_points,
    round(wins / nullif(matches_played, 0), 3) as win_rate,
    round((wins * 3 + draws) / nullif(matches_played, 0), 2) as points_per_game,
    round(goals_scored / nullif(matches_played, 0), 2) as goals_scored_per_match,
    round(goals_conceded / nullif(matches_played, 0), 2) as goals_conceded_per_match
from {{ ref('fact_club_season') }}
