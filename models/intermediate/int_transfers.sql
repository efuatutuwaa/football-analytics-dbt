-- Model: int_transfers
-- Grain: 1 row per player transfer (player_id, transfer_date, new_team_id, previous_team_id)
-- Materialization: table
-- Sources: stg_transfers (primary)
-- Purpose:
--   Enriches staging transfer records with business logic classifications.
--   Splits the raw transfer_type field (which the API uses for both the fee amount
--   and the transfer type) into a normalized transfer_type (permanent/loan/loan_return/
--   free/unknown) and transfer_fee (the raw monetary string where applicable).
--   Adds transfer_window tagging (summer/winter/emergency) based on transfer_date month.
--   Feeds int_player_club_periods (for club stint periods) and mart_transfer_window
--   (for transfer window analysis).
--
-- Raw transfer_type values observed in source data:
--   Loan, Back from Loan, Return from loan → loan / loan_return
--   Free, Free Transfer, Free agent        → free
--   Transfer                               → permanent (fee undisclosed)
--   € 1M, € 5M, € 75M, etc.              → permanent (fee = raw string)
--   N/A, None, -, Raise                   → unknown
--
-- Deduplication notes:
--   stg_transfers deduplicates on (player_id, transfer_date, team_in_id, team_out_id) — one row
--   per raw transfer record. This model applies a tighter dedup on (player_id, new_team_id,
--   transfer_date), dropping previous_team_id. Reason: the API occasionally returns the same
--   transfer event twice with different previous_team values (a data error). int_player_club_periods
--   keys on (player_id, new_team_id, transfer_date) with no previous_team, so those duplicates
--   would collide there. Records with no destination team (new_team_id is null) are also excluded
--   — these are free agent releases with no club to link a stint to.

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
