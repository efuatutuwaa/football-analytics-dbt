-- Model: fact_player_market_value_period
-- Grain: 1 row per fee-bearing permanent transfer (player_id, team_id, transfer_date)
-- Materialization: table (football_core) — physical table for transfer-fee analysis
-- Sources:
--   int_player_market_value_periods — primary; permanent transfers with non-null transfer_fee
-- Purpose:
--   Core fact for paid permanent transfers only. Each row is one fee-bearing move — raw fee
--   string from the API (e.g. '€ 75M'), destination and previous club, transfer window.
--   Join dim_player on player_id and dim_club on team_id (destination) in marts or BI.
--   schema.yml relationship tests use severity warn — player/club may not be in dims if outside scope.
--   Do not join int_transfers or int_player_market_value_periods from the consumption layer.
-- Output columns (from int_player_market_value_periods):
--   player_id, player_name, team_id, team_name, previous_team_id, previous_team_name
--   transfer_date, transfer_fee, transfer_type, transfer_window, ingested_at
-- Excludes:
--   Loans, frees, loan returns, undisclosed permanents — no core fact yet; intermediate int_transfers only
--   Club stint timelines — no core fact yet; intermediate int_player_club_periods (all moves, not fee-only)
-- Design notes:
--   Thin exposure layer: fee filter and column rename (new_team_id → team_id) live in intermediate.
--   transfer_fee is not parsed to numeric here — marts should document currency/parsing rules.
--   transfer_type should be permanent for all rows; loans/frees never appear in this fact.
-- Consumers (consumption layer):
--   mart_transfer_window, mart_player_valuation, mart_player_value_changes, transfer spend analysis

{{ config(materialized='table') }}

select
    -- identifiers
    player_id,
    team_id,
    transfer_date,
    -- player and clubs
    player_name,
    team_name,
    previous_team_id,
    previous_team_name,
    -- transfer details
    transfer_fee,
    transfer_type,
    transfer_window,
    -- metadata
    ingested_at
from {{ ref('int_player_market_value_periods') }}
