-- Model: mart_transfer_window
-- Grain: 1 row per fee-bearing permanent transfer (player_id, team_id, transfer_date)
-- Materialization: table (football_marts) — reporting layer; join dim_player and dim_club in BI
-- Sources (consumption layer only — do not ref int_*):
--   fact_player_market_value_period — primary; paid permanent moves with API fee string
--   dim_player                      — optional enrich on player_id
--   dim_club                        — optional enrich on team_id / previous_team_id
-- Purpose:
--   Transfer signing explorer: destination, origin, fee string, and calendar attributes for
--   summer/winter/emergency window analysis. v1 is fee-bearing permanents only — loans, frees,
--   and undisclosed permanents are not in fact_player_market_value_period yet.
-- Output columns:
--   player_id, player_name, team_id, team_name, previous_team_id, previous_team_name
--   transfer_date, transfer_year, transfer_month, transfer_fee, transfer_type, transfer_window
--   ingested_at
-- Excludes:
--   Loans, frees, loan returns — no core fact in v1 (see int_transfers in intermediate only)
--   Club stint timelines — int_player_club_periods (not for consumption layer)
-- SQL patterns: thin passthrough + date parts (no fee parsing to numeric in v1)
-- Design notes:
--   transfer_fee remains raw API text (e.g. '€ 75M') — parse in BI or a future macro if needed.
--   transfer_window: summer (Jun–Aug), winter (Jan), emergency (other months) — set upstream.
-- Consumers:
--   Streamlit transfer window page, top signings by window, portfolio transfers section

{{ config(materialized='table') }}

select
    player_id,
    player_name,
    team_id,
    team_name,
    previous_team_id,
    previous_team_name,
    transfer_date,
    year(transfer_date) as transfer_year,
    month(transfer_date) as transfer_month,
    transfer_fee,
    transfer_type,
    transfer_window,
    ingested_at
from {{ ref('fact_player_market_value_period') }}
