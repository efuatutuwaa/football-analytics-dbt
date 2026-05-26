-- Model: mart_continental_cups
-- Grain: 1 row per national team per continental tournament per edition per round stage
--        (team_id, league_id, league_season, league_round)
-- Materialization: table (football_marts) — round-by-round progression (v1: Euros only)
-- Sources (consumption layer only — do not ref int_*):
--   fact_national_team_run — primary; filter league_id = 4 in v1
--   dim_national_team      — optional enrich on team_id
--   dim_league             — optional enrich on league_id
-- Purpose:
--   Same structure as mart_world_cup but parameterised by league_id. v1 ships UEFA European
--   Championship only; v2 extends the WHERE league_id in (...) list for AFCON, Copa América, etc.
--   without changing grain or column layout.
-- Competitions:
--   v1: league_id = 4 (UEFA European Championship)
--   v2 (planned): add league_ids when those tournaments are ingested — see scripts/ingestion/constants.py
-- Output columns:
--   team_id, team_name, league_id, league_name, league_season, league_round, round_order
--   matches_in_round, wins, draws, losses, goals_scored, goals_conceded
--   group_name, group_position, is_eliminated_in_round, is_winner_in_round, ingested_at
--   (semantics identical to mart_world_cup — see that model header)
-- Round-level logic:
--   Pattern A — finished matches only: match_status_short in (FT, AET, PEN).
--   Pattern B — W/D/L from is_winner + goals (not match_result on fact).
--   Pattern C — max(team_name), max(league_name), max(group_name) in round_agg GROUP BY.
--   Pattern J — group by league_round; is_eliminated_in_round / is_winner_in_round flags. See README.
-- Excludes:
--   FIFA World Cup — mart_world_cup (league_id = 1)
--   Single-row edition summary — mart_national_team_results
-- SQL patterns: A, B, C, J — see models/marts/README.md
-- Design notes:
--   Consider a shared macro with mart_world_cup if both stay in sync — duplicate SQL intentional for v1 clarity.
-- Consumers:
--   Euros progression page, extensible to other confederation tournaments in v2

{{ config(materialized='table') }}

-- pattern A: finished Euros matches only (v1 league_id = 4)
with finished_matches as (
    select *
    from {{ ref('fact_national_team_run') }}
    where
        league_id = 4
        and match_status_short in ('FT', 'AET', 'PEN')
),

-- pattern B: W/D/L from perspective + goals
match_stats as (
    select
        *,
        case
            when is_winner then 'win'
            when goals_scored = goals_conceded then 'draw'
            else 'loss'
        end as match_result
    from finished_matches
),

-- pattern J + C: one row per nation × tournament × season × round; max() on non-key columns
round_agg as (
    select
        team_id,
        max(team_name) as team_name,
        league_id,
        max(league_name) as league_name,
        league_season,
        league_round,
        max(round_order) as round_order,
        count(*) as matches_in_round,
        sum(case when match_result = 'win' then 1 else 0 end) as wins,
        sum(case when match_result = 'draw' then 1 else 0 end) as draws,
        sum(case when match_result = 'loss' then 1 else 0 end) as losses,
        sum(goals_scored) as goals_scored,
        sum(goals_conceded) as goals_conceded,
        max(group_name) as group_name,
        max(group_position) as group_position,
        max(ingested_at) as ingested_at
    from match_stats
    group by team_id, league_id, league_season, league_round
),

team_max_round as (
    select
        team_id,
        league_id,
        league_season,
        max(round_order) as max_round_order
    from round_agg
    group by team_id, league_id, league_season
)

-- pattern J: exit / winner flags from deepest round vs Final bucket
select
    r.team_id,
    r.team_name,
    r.league_id,
    r.league_name,
    r.league_season,
    r.league_round,
    r.round_order,
    r.matches_in_round,
    r.wins,
    r.draws,
    r.losses,
    r.goals_scored,
    r.goals_conceded,
    r.group_name,
    r.group_position,
    r.round_order = t.max_round_order and r.losses > 0 as is_eliminated_in_round,
    r.league_round = 'Final' and r.wins > 0 as is_winner_in_round,
    r.ingested_at
from round_agg as r
inner join team_max_round as t
    on
        r.team_id = t.team_id
        and r.league_id = t.league_id
        and r.league_season = t.league_season
