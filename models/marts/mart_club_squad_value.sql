-- Model: mart_club_squad_value
-- Grain: 1 row per club per domestic league per season (team_id, league_id, league_season)
-- Materialization: table (football_marts) — reporting layer; join dim_club and dim_league in BI
-- Sources (consumption layer only — do not ref int_*):
--   mart_player_season              — primary roster proxy (players with league appearances)
--   fact_player_market_value_period — inbound transfer fees (raw € string → parsed in this mart)
--   dim_club                        — optional enrich on team_id
-- Purpose:
--   Estimated squad transfer-fee footprint per club-season for portfolio / Streamlit spend views.
--   Sums the latest known fee when a player joined the club (inbound) and, where missing, the
--   player's latest global fee-bearing move as a weak fallback. Not official market valuations —
--   API player market_value snapshots are not in core facts yet (see snapshots/scd_player_market_value).
-- Competitions (league_id):
--   39 Premier League, 61 Ligue 1, 78 Bundesliga, 135 Serie A, 140 La Liga
-- Output columns:
--   team_id, team_name, league_id, league_name, league_season
--   squad_players — distinct players in mart_player_season for this club × league × season
--   players_with_inbound_fee, players_with_estimated_fee — coverage counts
--   squad_inbound_fee_eur — sum of latest inbound fee at this club only (null fees excluded)
--   squad_estimated_fee_eur — sum of coalesce(inbound, latest global fee) per player
--   avg_estimated_fee_eur_per_player — squad_estimated_fee_eur / players_with_estimated_fee
--   max_inbound_fee_eur — largest single inbound signing fee at the club (all time in fact, not season-scoped)
--   inbound_spend_in_season_eur — sum of inbound fees where year(transfer_date) = league_season
-- Aggregation logic:
--   Pattern L — parse transfer_fee API strings (e.g. '€ 75M') to transfer_fee_eur in fee_parsed CTE.
--   Latest inbound fee per (player_id, team_id) and latest global fee per player_id via row_number().
--   estimated_fee_eur = coalesce(inbound, global) per squad player; sums at club-season grain.
--   Pattern C — max(team_name), max(league_name) in final GROUP BY (names constant per team_id / league_id).
-- Excludes:
--   Loans, frees, undisclosed permanents — not in fact_player_market_value_period
--   Current roster snapshot — stg_team_squads (no core fact in v1); season appearances define squad
--   Official market values — future scd_player_market_value; player-season proxy — mart_player_valuation
-- SQL patterns: C, L — see models/marts/README.md
-- Design notes:
--   Inbound fee = latest fact row per (player_id, team_id) by transfer_date desc.
--   Global fallback = latest fact row per player_id across all clubs.
--   squad_estimated_fee_eur can overstate when a player has no inbound fee but a large fee elsewhere.
--   inbound_spend_in_season_eur is calendar-year spend, not league-season match dates.
-- Consumers:
--   Streamlit club valuation page, squad spend vs mart_club_season performance, portfolio transfers section

{{ config(materialized='table') }}

{% set domestic_league_ids = [39, 61, 78, 135, 140] %}

with season_squad as (
    select
        player_id,
        player_name,
        team_id,
        team_name,
        league_id,
        league_name,
        league_season
    from {{ ref('mart_player_season') }}
    where league_id in ({{ domestic_league_ids | join(', ') }})
),

-- pattern L: parse raw € fee strings to numeric EUR (see models/marts/README.md)
fee_parsed as (
    select
        *,
        {{ parse_transfer_fee_eur('transfer_fee') }} as transfer_fee_eur
    from {{ ref('fact_player_market_value_period') }}
    where transfer_fee is not null
),

latest_inbound_fee as (
    select
        player_id,
        team_id,
        transfer_date as inbound_transfer_date,
        transfer_fee,
        transfer_fee_eur
    from fee_parsed
    qualify row_number() over (
        partition by player_id, team_id
        order by transfer_date desc, ingested_at desc
    ) = 1
),

latest_global_fee as (
    select
        player_id,
        transfer_date as latest_transfer_date,
        team_id as latest_fee_team_id,
        transfer_fee as latest_transfer_fee,
        transfer_fee_eur as latest_transfer_fee_eur
    from fee_parsed
    qualify row_number() over (
        partition by player_id
        order by transfer_date desc, ingested_at desc
    ) = 1
),

inbound_spend_by_year as (
    select
        team_id,
        year(transfer_date) as league_season,
        sum(transfer_fee_eur) as inbound_spend_in_season_eur
    from fee_parsed
    group by team_id, year(transfer_date)
),

player_squad_fees as (
    select
        s.player_id,
        s.player_name,
        s.team_id,
        s.team_name,
        s.league_id,
        s.league_name,
        s.league_season,
        i.inbound_transfer_date,
        i.transfer_fee as inbound_transfer_fee,
        i.transfer_fee_eur as inbound_fee_eur,
        g.latest_transfer_date,
        g.latest_transfer_fee,
        g.latest_transfer_fee_eur,
        coalesce(i.transfer_fee_eur, g.latest_transfer_fee_eur) as estimated_fee_eur
    from season_squad as s
    left join latest_inbound_fee as i
        on
            s.player_id = i.player_id
            and s.team_id = i.team_id
    left join latest_global_fee as g
        on s.player_id = g.player_id
)

-- pattern C: max(team_name) / max(league_name) — required by GROUP BY, not a business max
select
    p.team_id,
    max(p.team_name) as team_name,
    p.league_id,
    max(p.league_name) as league_name,
    p.league_season,
    count(distinct p.player_id) as squad_players,
    count(distinct case when p.inbound_fee_eur is not null then p.player_id end) as players_with_inbound_fee,
    count(distinct case when p.estimated_fee_eur is not null then p.player_id end) as players_with_estimated_fee,
    round(sum(p.inbound_fee_eur), 0) as squad_inbound_fee_eur,
    round(sum(p.estimated_fee_eur), 0) as squad_estimated_fee_eur,
    round(
        sum(p.estimated_fee_eur) / nullif(
            count(distinct case when p.estimated_fee_eur is not null then p.player_id end),
            0
        ),
        0
    ) as avg_estimated_fee_eur_per_player,
    round(max(p.inbound_fee_eur), 0) as max_inbound_fee_eur,
    round(coalesce(max(sp.inbound_spend_in_season_eur), 0), 0) as inbound_spend_in_season_eur
from player_squad_fees as p
left join inbound_spend_by_year as sp
    on
        p.team_id = sp.team_id
        and p.league_season = sp.league_season
group by
    p.team_id,
    p.league_id,
    p.league_season
