-- Model: mart_player_valuation
-- Grain: 1 row per player per club per league per season (player_id, team_id, league_id, league_season)
-- Materialization: table (football_marts) — reporting layer; join dim_player in BI
-- Sources (consumption layer only — do not ref int_*):
--   mart_player_season              — primary; player-season stint anchor (all tracked competitions)
--   fact_player_market_value_period — fee-bearing permanent transfers; parsed to EUR in this mart
--   dim_player                      — optional enrich on player_id
-- Purpose:
--   Player valuation proxy per league-season stint for scout and transfer dashboards. v1 uses
--   reported transfer fees only — not Transfermarkt-style market_value (no column in API raw_players;
--   scd_player_market_value snapshot is planned but not populated). Coalesces inbound fee at the
--   stint club with latest global fee as fallback.
-- Output columns:
--   player_id, player_name, team_id, team_name, league_id, league_name, league_season
--   appearances, goals, assists, minutes_played — performance context from mart_player_season
--   inbound_transfer_fee, inbound_transfer_fee_eur, inbound_transfer_date
--   latest_global_transfer_fee, latest_global_transfer_fee_eur, latest_global_transfer_date, latest_global_team_id
--   estimated_valuation_eur — coalesce(inbound_fee_eur, latest_global_fee_eur)
--   valuation_basis — inbound_transfer_fee | latest_global_transfer_fee | null
-- Valuation logic:
--   Pattern L — parse transfer_fee strings to transfer_fee_eur (see models/marts/README.md).
--   Inbound = latest fee when player joined team_id; global = latest fee anywhere for player_id.
-- Excludes:
--   Loans, frees, undisclosed permanents — not in fact_player_market_value_period
--   Official market-value time series — future snapshots/scd_player_market_value
--   Transfer fee deltas — mart_player_value_changes
-- SQL patterns: L — see models/marts/README.md
-- Design notes:
--   Same fee semantics as mart_club_squad_value but player-season grain, not club aggregate.
--   Players without any fee-bearing move have null estimated_valuation_eur.
--   National-team team_ids in mart_player_season may not match dim_club — expected.
-- Consumers:
--   Streamlit player scout valuation column, top signings by league, portfolio transfer section

{{ config(materialized='table') }}

with season_stints as (
    select
        player_id,
        player_name,
        team_id,
        team_name,
        league_id,
        league_name,
        league_season,
        appearances,
        goals,
        assists,
        minutes_played
    from {{ ref('mart_player_season') }}
),

-- pattern L: parse raw € fee strings to numeric EUR (see models/marts/README.md)
fee_parsed as (
    select
        player_id,
        team_id,
        transfer_date,
        transfer_fee,
        {{ parse_transfer_fee_eur('transfer_fee') }} as transfer_fee_eur,
        ingested_at
    from {{ ref('fact_player_market_value_period') }}
    where transfer_fee is not null
),

latest_inbound_fee as (
    select
        player_id,
        team_id,
        transfer_date as inbound_transfer_date,
        transfer_fee as inbound_transfer_fee,
        transfer_fee_eur as inbound_transfer_fee_eur
    from fee_parsed
    qualify row_number() over (
        partition by player_id, team_id
        order by transfer_date desc, ingested_at desc
    ) = 1
),

latest_global_fee as (
    select
        player_id,
        transfer_date as latest_global_transfer_date,
        team_id as latest_global_team_id,
        transfer_fee as latest_global_transfer_fee,
        transfer_fee_eur as latest_global_transfer_fee_eur
    from fee_parsed
    qualify row_number() over (
        partition by player_id
        order by transfer_date desc, ingested_at desc
    ) = 1
)

select
    s.player_id,
    s.player_name,
    s.team_id,
    s.team_name,
    s.league_id,
    s.league_name,
    s.league_season,
    s.appearances,
    s.goals,
    s.assists,
    s.minutes_played,
    i.inbound_transfer_fee,
    i.inbound_transfer_fee_eur,
    i.inbound_transfer_date,
    g.latest_global_transfer_fee,
    g.latest_global_transfer_fee_eur,
    g.latest_global_transfer_date,
    g.latest_global_team_id,
    coalesce(i.inbound_transfer_fee_eur, g.latest_global_transfer_fee_eur) as estimated_valuation_eur,
    case
        when i.inbound_transfer_fee_eur is not null then 'inbound_transfer_fee'
        when g.latest_global_transfer_fee_eur is not null then 'latest_global_transfer_fee'
    end as valuation_basis
from season_stints as s
left join latest_inbound_fee as i
    on
        s.player_id = i.player_id
        and s.team_id = i.team_id
left join latest_global_fee as g
    on s.player_id = g.player_id
