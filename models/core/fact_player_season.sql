-- Model: fact_player_season
-- Grain: 1 row per player per club per league per season (player_id, team_id, league_id, league_season)
-- Materialization: table (football_core) — physical table for player season summaries
-- Sources:
--   int_player_season_metrics — primary; season totals aggregated from int_player_match_stats
-- Purpose:
--   Core fact for player performance at season grain. Mid-season transfers produce separate rows
--   per club. Metrics are derived in dbt from match-level player stats (not API season endpoints).
--   Join dim_player on player_id, dim_club on team_id, dim_league on league_id in marts or BI (left joins).
--   schema.yml relationship tests use severity warn: national-team team_ids (league 1, 4) are not in
--   dim_club; player_ids from match stats may be missing from dim_player if not in raw_players ingest.
-- Output columns (from int_player_season_metrics):
--   player_id, player_name, team_id, team_name, league_id, league_name, league_season
--   appearances, total_starts, minutes_played, total_shots, shots_on_target
--   goals, assists, yellow_cards, red_cards, total_passes, total_tackles, interceptions
--   successful_dribbles, avg_rating
-- Excludes:
--   Match-level detail — use fact_player_match_stats
--   Club team season totals — use fact_club_season
-- Design notes:
--   Thin exposure layer: aggregation lives in int_player_season_metrics.
--   appearances = count of match rows; total_starts excludes is_substitute = true.
--   avg_rating is mean of per-match rating (double; try_cast in stg_player_statistics handles the
--   API '-' sentinel, which becomes null and is excluded from avg()).
-- Consumers (consumption layer):
--   mart_player_season, mart_domestic_league_top_scorers, season-on-season player comparisons

{{ config(materialized='table') }}

select
    -- identifiers
    player_id,
    team_id,
    league_id,
    league_season,
    -- player and club
    player_name,
    team_name,
    league_name,
    -- season totals
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
    avg_rating
from {{ ref('int_player_season_metrics') }}
