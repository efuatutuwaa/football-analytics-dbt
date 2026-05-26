-- Model: mart_player_season
-- Grain: 1 row per player per club per league per season (player_id, team_id, league_id, league_season)
-- Materialization: table (football_marts) — reporting layer; join dim_player, dim_club, dim_league in BI
-- Sources (consumption layer only — do not ref int_*):
--   fact_player_season — primary; thin enrich with per-90 and per-appearance rates
--   dim_player         — optional enrich on player_id (severity warn on fact if player missing from dim)
--   dim_club           — optional enrich on team_id (national-team team_ids may not be in dim_club)
-- Purpose:
--   Player season leaderboard mart: goals, assists, minutes, cards, and derived rates for top-scorer
--   tables and scout views. Mid-season transfers produce separate rows per club.
-- Output columns:
--   player_id, player_name, team_id, team_name, league_id, league_name, league_season
--   appearances, total_starts, minutes_played, goals, assists, yellow_cards, red_cards
--   total_shots, shots_on_target, total_passes, total_tackles, interceptions, successful_dribbles, avg_rating
--   goals_per_90, assists_per_90, minutes_per_appearance, shot_conversion_rate
-- Excludes:
--   Match-level rows — mart_player_matchday, fact_player_match_stats
--   Club season totals — mart_club_season
--   Transfer fees / valuation proxy — mart_player_valuation, mart_transfer_window
-- SQL patterns: thin passthrough + derived metrics
-- Design notes:
--   goals_per_90 and assists_per_90 use minutes_played / 90 as denominator; null when no minutes.
--   shot_conversion_rate = goals / total_shots when shots > 0.
--   avg_rating is mean of per-match ratings from upstream (null ratings excluded from avg).
-- Consumers:
--   mart_domestic_league_top_scorers, Streamlit player scout, portfolio player stats section

{{ config(materialized='table') }}

select
    player_id,
    player_name,
    team_id,
    team_name,
    league_id,
    league_name,
    league_season,
    appearances,
    total_starts,
    minutes_played,
    total_shots,
    shots_on_target,
    goals,
    assists,
    yellow_cards,
    red_cards,
    total_passes,
    total_tackles,
    interceptions,
    successful_dribbles,
    avg_rating,
    round(goals / nullif(minutes_played / 90.0, 0), 2) as goals_per_90,
    round(assists / nullif(minutes_played / 90.0, 0), 2) as assists_per_90,
    round(minutes_played / nullif(appearances, 0), 1) as minutes_per_appearance,
    round(goals / nullif(total_shots, 0), 3) as shot_conversion_rate
from {{ ref('fact_player_season') }}
