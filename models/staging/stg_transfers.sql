-- Model: stg_transfers
-- Layer: staging
-- Grain: 1 row per player_id + transfer_date + new_team_id + previous_team_id
-- Materialization: view
-- Source: football_raw.raw_transfers
-- Purpose:
--   Player transfer history as returned by the API. Raw transfer_type mixes fee strings and
--   type labels — normalized in int_transfers, not here.
-- Transformations:
--   Renames team_in/out to new_team_id / previous_team_id; trims names and transfer_type;
--   dedup via qualify row_number() on (player_id, transfer_date, team_in_id, team_out_id) by ingested_at desc.
-- Downstream:
--   int_transfers → int_player_club_periods, int_player_market_value_periods, mart_transfer_window
-- Notes:
--   Ingestion runs on a transfer-window-aware schedule. Rows with null new_team_id kept for audit;
--   int_transfers excludes them when building club stints.

{{ config(materialized='view') }}

with source as (
    select
        -- identifiers
        player_id,
        -- player details
        trim(player_name) as player_name,
        -- transfer details
        transfer_date,
        trim(transfer_type) as transfer_type,
        team_in_id as new_team_id,
        trim(team_in_name) as new_team_name,
        team_out_id as previous_team_id,
        trim(team_out_name) as previous_team_name,
        -- metadata
        cast(last_updated as timestamp) as last_updated,
        cast(ingested_at as timestamp) as ingested_at
    from {{ source('football_raw', 'raw_transfers') }}
    qualify row_number() over (
        partition by player_id, transfer_date, team_in_id, team_out_id
        order by ingested_at desc
    ) = 1
)

select * from source
