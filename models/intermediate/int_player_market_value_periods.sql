-- Model: int_player_market_value_periods
-- Grain: 1 row per fee-bearing permanent transfer (player_id, new_team_id, transfer_date)
-- Materialization: table — subset of int_transfers
-- Sources: int_transfers where transfer_fee is not null (permanent moves with € amount in API string)
-- Purpose:
--   Fee-only transfer rows for market-value and spend analysis. Retains transfer_fee as raw API
--   string (e.g. '€ 75M') — parsing to numeric is a mart concern if needed.
-- Downstream:
--   fact_player_market_value_period (core), mart_transfer_window, transfer fee / top-signing analysis
-- Excludes:
--   Loans, frees, unknown types, undisclosed permanents (transfer_type = permanent but no fee string)
-- Notes:
--   Fee strings are not normalised to a single currency or numeric here — document assumptions in marts.

{{ config(materialized='table') }}

with transfers as (
    select *
    from {{ ref('int_transfers') }}
    where transfer_fee is not null
)

select
    -- identifiers
    player_id,
    player_name,
    new_team_id as team_id,
    new_team_name as team_name,
    previous_team_id,
    previous_team_name,
    -- transfer details
    transfer_date,
    transfer_fee,
    transfer_type,
    transfer_window,
    -- metadata
    ingested_at
from transfers
