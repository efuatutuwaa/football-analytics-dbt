-- Model: fact_player_match_stats
-- Grain: 1 row per player per fixture (fixture_id, player_id)
-- Materialization: table (football_core) — physical table for player match-level analysis
-- Sources:
--   int_player_match_stats — primary; per-match stats with fixture context from spine at intermediate
-- Purpose:
--   Core fact for player performance in a single match. Carries minutes, goals, assists, cards,
--   passing, defensive actions, and denormalised match context (league, opponent, home/away, result).
--   Join dim_player on player_id; dim_club on team_id for club competitions, dim_national_team on
--   team_id for World Cup / Euros fixtures (team_id references whichever dim applies — verified no
--   orphaned IDs). Join fact_fixture on fixture_id for match context.
--   Do not join int_fixture_spine or int_player_match_stats from the consumption layer.
-- Output columns (from int_player_match_stats):
--   fixture_id, player_id, team_id, player_name, team_name, jersey_number, player_position, rating
--   is_captain, is_substitute, league_id, league_name, league_season, league_round, match_date
--   is_home, opponent_team_id, opponent_team_name, match_result
--   minutes_played, offsides, total_shots, shots_on_target, goals_scored, goals_conceded, assists, saves
--   total_passes, key_passes, pass_accuracy_pct, total_tackles, blocks, interceptions
--   total_duels, duels_won, dribbles_attempted, successful_dribbles, dribbles_past
--   fouls_drawn, fouls_committed, yellow_card_count, red_card_count
--   penalties_won, penalties_committed, penalties_scored, penalties_missed, penalties_saved, ingested_at
-- Excludes:
--   Season rollups — use fact_player_season
--   Team-level match stats — use fact_club_match_stats
--   Event-level goals/cards timeline — use fact_fixture_events
-- Design notes:
--   Thin exposure layer: fixture context join and match_result CASE live in intermediate.
--   match_result is null when the fixture has no winner yet (not finished or draw with null flags).
--   rating is double (try_cast in stg_player_statistics; API '-' sentinel becomes null).
--   Deduped in intermediate to latest ingested_at per fixture_id + player_id.
-- Consumers (consumption layer):
--   mart_player_matchday, mart_player_season, Streamlit player explorer
-- Build path (intermediate only): int_player_season_metrics aggregates int_player_match_stats, then this fact.

{{ config(materialized='table') }}

select
    -- identifiers
    fixture_id,
    player_id,
    team_id,
    -- player and club
    player_name,
    team_name,
    jersey_number,
    player_position,
    rating,
    is_captain,
    is_substitute,
    -- competition and match context
    league_id,
    league_name,
    league_season,
    league_round,
    match_date,
    is_home,
    opponent_team_id,
    opponent_team_name,
    match_result,
    -- match statistics
    minutes_played,
    offsides,
    total_shots,
    shots_on_target,
    goals_scored,
    goals_conceded,
    assists,
    saves,
    total_passes,
    key_passes,
    pass_accuracy_pct,
    total_tackles,
    blocks,
    interceptions,
    total_duels,
    duels_won,
    dribbles_attempted,
    successful_dribbles,
    dribbles_past,
    fouls_drawn,
    fouls_committed,
    yellow_card_count,
    red_card_count,
    penalties_won,
    penalties_committed,
    penalties_scored,
    penalties_missed,
    penalties_saved,
    -- metadata
    ingested_at
from {{ ref('int_player_match_stats') }}
