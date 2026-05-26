-- Model: mart_club_domestic_cup_performance
-- Grain: 1 row per club per domestic cup per season (team_id, league_id, league_season)
-- Materialization: table (football_marts) — reporting layer; join dim_club and dim_league in BI
-- Sources (consumption layer only — do not ref int_*):
--   fact_club_domestic_cup_run — primary; aggregate finished match rows to campaign grain
--   dim_club                 — optional enrich on team_id
--   dim_league               — optional enrich on league_id
-- Purpose:
--   Season-level summary of each club's domestic knockout campaign: matches played, W/D/L, goals,
--   deepest round reached, and whether they won the cup. Use for cup-run charts, giant-killing lists,
--   and joining to mart_club_honours or fact_club_season for double/treble context.
-- Competitions (league_id):
--   45 FA Cup, 48 Carabao Cup, 66 Coupe de France, 81 DFB-Pokal, 137 Coppa Italia, 143 Copa del Rey
--   England is the only country with two domestic cups in this dataset.
-- Output columns:
--   team_id, team_name, league_id, league_name, league_season
--   matches_played, wins, draws, losses, goals_scored, goals_conceded
--   farthest_round, farthest_round_order — label and rank from deepest finished match in the season
--   was_cup_winner — true if club won the Final (league_round = 'Final' and is_winner on a finished match)
--   ingested_at — max from underlying fact rows
-- Aggregation logic:
--   Only finished matches: match_status_short in (FT, AET, PEN).
--   W/D/L: win if is_winner; draw if goals_scored = goals_conceded; else loss.
--   farthest_round: one row per campaign via row_number() on round_order desc (see farthest_round_label CTE;
--     row_number never ties — fixture_id breaks remaining duplicates). See models/marts/README.md.
--   max(team_name) / max(league_name): required by GROUP BY — not a business rule; names are constant per team_id.
--   was_cup_winner: separate check on Final rows — not the same as is_farthest_round on the fact.
-- Excludes:
--   Match-level cup rows — fact_club_domestic_cup_run (two rows per fixture, home/away perspective)
--   European tournaments — mart_club_european_performance
--   Domestic league season totals — fact_club_season
-- SQL patterns: A, B, C, D — see models/marts/README.md
-- Design notes:
--   fact_club_domestic_cup_run is two rows per fixture; this mart aggregates to one campaign row.
--   is_farthest_round on the fact is true on all matches in the deepest round — this mart uses
--   max(round_order) for farthest_round instead. Replays and two-legged ties may inflate matches_played.
--   fact_standings is a point-in-time snapshot if used alongside for league context — document in dashboards.
-- Consumers:
--   Streamlit cup page, mart_club_honours (domestic_cups_won), portfolio domestic cup section

{{ config(materialized='table') }}

-- pattern A: finished domestic cup matches only
with finished_matches as (
    select *
    from {{ ref('fact_club_domestic_cup_run') }}
    where match_status_short in ('FT', 'AET', 'PEN')
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

-- pattern C: campaign totals; max() on names for GROUP BY
campaign_agg as (
    select
        team_id,
        max(team_name) as team_name,
        league_id,
        max(league_name) as league_name,
        league_season,
        count(*) as matches_played,
        sum(case when match_result = 'win' then 1 else 0 end) as wins,
        sum(case when match_result = 'draw' then 1 else 0 end) as draws,
        sum(case when match_result = 'loss' then 1 else 0 end) as losses,
        sum(goals_scored) as goals_scored,
        sum(goals_conceded) as goals_conceded,
        max(round_order) as farthest_round_order,
        max(ingested_at) as ingested_at
    from match_stats
    group by team_id, league_id, league_season
),

-- pattern D: deepest round label (row_number on round_order desc)
farthest_round_label as (
    select
        team_id,
        league_id,
        league_season,
        league_round as farthest_round
    from match_stats
    qualify row_number() over (
        partition by team_id, league_id, league_season
        order by round_order desc, match_date desc, fixture_id desc
    ) = 1
),

final_winners as (
    select
        team_id,
        league_id,
        league_season,
        true as was_cup_winner
    from finished_matches
    where
        league_round = 'Final'
        and is_winner = true
    group by team_id, league_id, league_season
)

select
    a.team_id,
    a.team_name,
    a.league_id,
    a.league_name,
    a.league_season,
    a.matches_played,
    a.wins,
    a.draws,
    a.losses,
    a.goals_scored,
    a.goals_conceded,
    f.farthest_round,
    a.farthest_round_order,
    coalesce(w.was_cup_winner, false) as was_cup_winner,
    a.ingested_at
from campaign_agg as a
inner join farthest_round_label as f
    on
        a.team_id = f.team_id
        and a.league_id = f.league_id
        and a.league_season = f.league_season
left join final_winners as w
    on
        a.team_id = w.team_id
        and a.league_id = w.league_id
        and a.league_season = w.league_season
