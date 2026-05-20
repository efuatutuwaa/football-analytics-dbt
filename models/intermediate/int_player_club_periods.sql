-- Model: int_player_club_periods
-- Grain: 1 row per player per club stint (player_id, team_id, transfer_date)
-- Materialization: table — lead() backfills period_end_date on historical rows when a new
--                  transfer arrives; incremental merge cannot handle that backfill
-- Sources: int_transfers (primary)
-- Purpose:
--   Derives club stint periods from transfer records. For each transfer, the player
--   joined the new club on transfer_date (period_start_date). The period_end_date is
--   the transfer_date of their next move, derived using a lead() window function
--   partitioned by player_id and ordered by transfer_date. A null period_end_date
--   means the player is still at that club.
--   Feeds int_player_match_stats and mart models that need to link a player's
--   match appearance to their club at the time.

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
