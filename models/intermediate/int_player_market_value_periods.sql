-- Model: int_player_market_value_periods
-- Grain: 1 row per player transfer with a recorded fee (player_id, new_team_id, transfer_date)
-- Materialization: table
-- Sources: int_transfers (primary, filtered to transfers with a non-null transfer_fee)
-- Purpose:
--   Filters int_transfers to only fee-bearing permanent transfers for market value
--   trend analysis. Captures the monetary fee, club moved to/from, and transfer window.
--   Feeds mart_transfer_window for fee distribution and player value tracking over time.

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
