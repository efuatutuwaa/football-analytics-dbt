-- Model: int_player_club_periods
-- Grain: 1 row per player per club stint (player_id, team_id / new_team_id, transfer_date as period_start)
-- Materialization: table (full refresh) — lead() must rewrite period_end_date on prior rows when new transfers ingest
-- Sources: int_transfers (primary)
-- Purpose:
--   Contiguous club stints for each player from transfer history.
--   period_start_date = transfer_date of the move in; period_end_date = lead(transfer_date) per player
--   (null period_end_date = still at club).
-- Downstream:
--   fact_player_club_period (core consumption), marts linking appearances to club at match date
-- Notes:
--   Cannot be incremental — a new transfer backfills end dates on earlier stints.
-- Excludes: Loan return semantics beyond transfer_type — interpret transfer_type from int_transfers

{{ config(materialized='table') }}

select
    -- identifiers
    player_id,
    player_name,
    new_team_id as team_id,
    new_team_name as team_name,
    previous_team_id,
    previous_team_name,
    -- transfer context
    transfer_date as period_start_date,
    lead(transfer_date) over (
        partition by player_id
        order by transfer_date
    ) as period_end_date,
    transfer_type,
    transfer_fee,
    transfer_window,
    -- metadata
    ingested_at
from {{ ref('int_transfers') }}
