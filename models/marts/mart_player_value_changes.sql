-- Model: mart_player_value_changes
-- Grain: 1 row per fee-bearing permanent transfer (player_id, team_id, transfer_date)
-- Materialization: table (football_marts) — reporting layer; join dim_player and dim_club in BI
-- Sources (consumption layer only — do not ref int_*):
--   fact_player_market_value_period — primary; ordered fee moves per player
--   dim_player                      — optional enrich on player_id
-- Purpose:
--   Transfer-fee change timeline for risers/fallers lists: each paid move vs the player's prior
--   fee-bearing move (not calendar market-value YoY — API has no market_value field). Use for
--   "biggest fee jump since last transfer" dashboards until scd_player_market_value exists.
-- Output columns:
--   player_id, player_name, team_id, team_name, previous_team_id, previous_team_name
--   transfer_date, transfer_year, transfer_window, transfer_fee, transfer_fee_eur
--   transfer_sequence — 1-based order of fee-bearing moves for this player
--   prior_transfer_date, prior_transfer_fee, prior_transfer_fee_eur
--   fee_change_eur, fee_change_pct — vs prior move (null on first fee-bearing transfer)
--   days_since_prior_transfer
--   is_first_fee_move, is_fee_increase, is_fee_decrease
-- Transfer timeline logic:
--   Pattern L — parse transfer_fee to transfer_fee_eur (see models/marts/README.md).
--   Pattern M — lag(prior fee) over player_id ordered by transfer_date, ingested_at.
-- Excludes:
--   Players with only one fee move still appear — deltas null; filter is_fee_increase in BI for risers
--   Loans, frees — not in fact_player_market_value_period
--   Point-in-time valuation by season — mart_player_valuation
--   Official market-value deltas — future scd_player_market_value
-- SQL patterns: L, M — see models/marts/README.md
-- Design notes:
--   fee_change_pct = (current - prior) / prior * 100 when prior > 0; null otherwise.
--   Moves on same transfer_date deduped upstream on fact grain — one row per player × destination × date.
-- Consumers:
--   Streamlit biggest risers/fallers, transfer fee jump charts, portfolio transfers section

{{ config(materialized='table') }}

-- pattern L: parse raw € fee strings to numeric EUR (see models/marts/README.md)
with fee_moves as (
    select
        player_id,
        player_name,
        team_id,
        team_name,
        previous_team_id,
        previous_team_name,
        transfer_date,
        year(transfer_date) as transfer_year,
        transfer_window,
        transfer_fee,
        {{ parse_transfer_fee_eur('transfer_fee') }} as transfer_fee_eur,
        ingested_at
    from {{ ref('fact_player_market_value_period') }}
    where transfer_fee is not null
),

-- pattern M: compare each move to the player's previous fee-bearing transfer
with_prior_fee as (
    select
        *,
        row_number() over (
            partition by player_id
            order by transfer_date, ingested_at
        ) as transfer_sequence,
        lag(transfer_date) over (
            partition by player_id
            order by transfer_date, ingested_at
        ) as prior_transfer_date,
        lag(transfer_fee) over (
            partition by player_id
            order by transfer_date, ingested_at
        ) as prior_transfer_fee,
        lag(transfer_fee_eur) over (
            partition by player_id
            order by transfer_date, ingested_at
        ) as prior_transfer_fee_eur
    from fee_moves
)

select
    player_id,
    player_name,
    team_id,
    team_name,
    previous_team_id,
    previous_team_name,
    transfer_date,
    transfer_year,
    transfer_window,
    transfer_fee,
    transfer_fee_eur,
    transfer_sequence,
    prior_transfer_date,
    prior_transfer_fee,
    prior_transfer_fee_eur,
    transfer_fee_eur - prior_transfer_fee_eur as fee_change_eur,
    round(
        (transfer_fee_eur - prior_transfer_fee_eur) / nullif(prior_transfer_fee_eur, 0) * 100,
        1
    ) as fee_change_pct,
    datediff(transfer_date, prior_transfer_date) as days_since_prior_transfer,
    prior_transfer_fee_eur is null as is_first_fee_move,
    prior_transfer_fee_eur is not null and transfer_fee_eur > prior_transfer_fee_eur as is_fee_increase,
    prior_transfer_fee_eur is not null and transfer_fee_eur < prior_transfer_fee_eur as is_fee_decrease
from with_prior_fee
