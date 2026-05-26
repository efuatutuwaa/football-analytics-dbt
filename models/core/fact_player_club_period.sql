-- Model: fact_player_club_period
-- Grain: 1 row per player per club stint (player_id, team_id, period_start_date)
-- Materialization: table (football_core) — consumption-layer exposure of transfer-derived stints
-- Sources:
--   int_player_club_periods — primary (thin passthrough below)
--   Lineage: stg_transfers → int_transfers (dedup, transfer_type) → int_player_club_periods (lead stints)
--   Not a dbt snapshot — see ADR 011
-- Purpose:
--   Transfer-based club history for BI and marts: when a player was at which club.
--   period_start_date = transfer in; period_end_date = next transfer (null = current stint).
--   This is the analytics answer to "player transfers over time" — not scd_player_club.
-- Output columns:
--   player_id, player_name, team_id, team_name, previous_team_id, previous_team_name
--   period_start_date, period_end_date, transfer_type, transfer_fee, transfer_window, ingested_at
-- Excludes:
--   Loans/frees semantics — see transfer_type; full history in int_transfers (intermediate only)
--   Squad snapshot drift without transfer — scd_player_club (dbt snapshot)
--   Fee-only rows — fact_player_market_value_period
-- Design notes:
--   Do not snapshot transfers: lead()-based periods must full-refresh when new transfers ingest.
--   Join matches: match_date >= period_start_date and (period_end_date is null or match_date < period_end_date).
--   Consumption layer: join dim_player, dim_club — do not join int_player_club_periods from BI.
-- Consumers:
--   Player timeline analysis, stint filters in Streamlit, portfolio transfer story

{{ config(materialized='table') }}

select
    player_id,
    player_name,
    team_id,
    team_name,
    previous_team_id,
    previous_team_name,
    period_start_date,
    period_end_date,
    transfer_type,
    transfer_fee,
    transfer_window,
    ingested_at
from {{ ref('int_player_club_periods') }}
