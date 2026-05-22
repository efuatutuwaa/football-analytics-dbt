-- Model: int_transfers
-- Grain: 1 row per player move (player_id, new_team_id, transfer_date) after dedup
-- Materialization: table — full refresh; lead()-based models downstream need consistent history
-- Sources: stg_transfers (primary; excludes rows where new_team_id is null)
-- Purpose:
--   Normalises API transfer_type (fee strings mixed with type labels) into:
--   transfer_type (permanent / loan / loan_return / free / unknown) and transfer_fee (raw € string).
--   Adds transfer_window: summer (Jun–Aug), winter (Jan), emergency (other months).
-- Downstream:
--   int_player_club_periods (stint start/end via lead), int_player_market_value_periods (fee rows),
--   mart_transfer_window
-- Filters:
--   new_team_id is not null — drops free-agent releases with no destination club
-- Dedup:
--   qualify row_number() over (player_id, new_team_id, transfer_date) — drops duplicate API rows
--   with conflicting previous_team_id (see stg_transfers vs this grain)
--
-- Raw transfer_type values observed in source data:
--   Loan, Back from Loan, Return from loan → loan / loan_return
--   Free, Free Transfer, Free agent        → free
--   Transfer                               → permanent (fee undisclosed)
--   € 1M, € 5M, € 75M, etc.              → permanent (fee = raw string)
--   N/A, None, -, Raise                   → unknown
--
{{ config(materialized='table') }}

with transfers as (
    select * from {{ ref('stg_transfers') }}
    where new_team_id is not null  -- exclude records with no destination team (free agent releases, API gaps)
),

classified as (
    select
        -- identifiers
        player_id,
        player_name,
        new_team_id,
        new_team_name,
        previous_team_id,
        previous_team_name,
        -- transfer details
        transfer_date,
        case
            when transfer_type = 'Loan' then 'loan'
            when transfer_type in ('Back from Loan', 'Return from loan') then 'loan_return'
            when transfer_type in ('Free', 'Free Transfer', 'Free agent') then 'free'
            when transfer_type = 'Transfer' then 'permanent'
            when transfer_type like '€%' then 'permanent'
            else 'unknown'
        end as transfer_type,
        case
            when transfer_type like '€%' then transfer_type
        end as transfer_fee,
        case
            when month(transfer_date) in (6, 7, 8) then 'summer'
            when month(transfer_date) = 1 then 'winter'
            else 'emergency'
        end as transfer_window,
        -- metadata
        last_updated,
        ingested_at
    from transfers
)

select * from classified
qualify row_number() over (
    partition by player_id, new_team_id, transfer_date
    order by ingested_at desc
) = 1
