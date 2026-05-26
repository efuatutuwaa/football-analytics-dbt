-- Model: mart_national_team_results
-- Grain: 1 row per national team per tournament edition (team_id, league_id, league_season)
-- Materialization: table (football_marts) — primary international summary mart
-- Sources (consumption layer only — do not ref int_*):
--   fact_national_team_run — primary; aggregate finished match rows to edition grain
--   dim_national_team      — optional enrich on team_id
--   dim_league             — optional enrich on league_id
-- Purpose:
--   One-row-per-nation-per-edition summary for World Cup and Euros: full campaign record, group
--   snapshot, farthest round, and tournament_placement (Winner through Group stage). Use before
--   mart_national_team_honours when you need all nations, not only podium finishers.
-- Competitions (league_id):
--   1 — FIFA World Cup (qualifying excluded upstream on fact)
--   4 — UEFA European Championship
-- Output columns:
--   team_id, team_name, league_id, league_name, league_season
--   matches_played, wins, draws, losses, goals_scored, goals_conceded
--   farthest_round, farthest_round_order
--   group_name, group_position, group_points, group_wins, group_draws, group_losses,
--   group_goals_for, group_goals_against, group_goal_difference
--   tournament_placement — Winner | Runner-up | Semi-finalist | Quarter-finalist | Round of 16 |
--                        Group stage | Eliminated (from deepest finished match — see below)
--   ingested_at
-- tournament_placement rules (deepest finished match per edition, tie-break match_date):
--   Winner         — league_round = 'Final' and is_winner
--   Runner-up      — league_round = 'Final' and not is_winner
--   Semi-finalist  — league_round = 'Semi-finals' and not is_winner
--   Quarter-finalist / Round of 16 — same pattern on respective rounds
--   Group stage    — deepest round label like 'Group%' (did not advance to knockout)
-- Edition-level logic:
--   Pattern A — finished matches only: match_status_short in (FT, AET, PEN).
--   Pattern B — W/D/L from is_winner + goals (not match_result on fact).
--   Pattern C — max(team_name), max(league_name) in campaign_agg GROUP BY.
--   Pattern D — farthest_round label via row_number on round_order desc (farthest_round_label CTE).
--   Pattern E — one group-stage snapshot row per edition (group_snapshot CTE).
--   Pattern F — tournament_placement CASE from deepest finished match (placement CTE). See README.
-- Excludes:
--   Round-by-round narrative — mart_world_cup, mart_continental_cups
--   Podium-only filter — mart_national_team_honours
--   Clubs — fact_club_* models
-- SQL patterns: A, B, C, D, E, F — see models/marts/README.md
-- Design notes:
--   No is_home on fact — neutral-site tournaments; venue from fact_fixture if needed.
--   is_farthest_round on the fact marks all matches in deepest round — this mart uses max(round_order).
--   3rd Place Final is not a separate placement label in v1.
-- Consumers:
--   International dashboards, feeds mart_national_team_honours, portfolio WC/Euros summary

{{ config(materialized='table') }}

-- pattern A: finished international matches only
with finished_matches as (
    select *
    from {{ ref('fact_national_team_run') }}
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

-- pattern C: edition totals; max() on names for GROUP BY
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

-- pattern E: latest group-stage row per edition (not summed group stats)
group_snapshot as (
    select
        team_id,
        league_id,
        league_season,
        group_name,
        group_position,
        group_points,
        group_wins,
        group_draws,
        group_losses,
        group_goals_for,
        group_goals_against,
        group_goal_difference
    from match_stats
    where
        group_name is not null
        or league_round like 'Group%'
    qualify row_number() over (
        partition by team_id, league_id, league_season
        order by match_date desc, fixture_id desc
    ) = 1
),

-- deepest match row (same row_number idea as D) — feeds pattern F
deepest_round_match as (
    select
        team_id,
        league_id,
        league_season,
        league_round,
        round_order,
        is_winner
    from match_stats
    qualify row_number() over (
        partition by team_id, league_id, league_season
        order by round_order desc, match_date desc, fixture_id desc
    ) = 1
),

-- pattern F: tournament_placement from deepest finished match
placement as (
    select
        team_id,
        league_id,
        league_season,
        case
            when league_round = 'Final' and is_winner then 'Winner'
            when league_round = 'Final' and not is_winner then 'Runner-up'
            when league_round = 'Semi-finals' and not is_winner then 'Semi-finalist'
            when league_round = 'Quarter-finals' and not is_winner then 'Quarter-finalist'
            when league_round = 'Round of 16' and not is_winner then 'Round of 16'
            when league_round like 'Group%' then 'Group stage'
            else 'Eliminated'
        end as tournament_placement
    from deepest_round_match
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
    g.group_name,
    g.group_position,
    g.group_points,
    g.group_wins,
    g.group_draws,
    g.group_losses,
    g.group_goals_for,
    g.group_goals_against,
    g.group_goal_difference,
    p.tournament_placement,
    a.ingested_at
from campaign_agg as a
inner join farthest_round_label as f
    on
        a.team_id = f.team_id
        and a.league_id = f.league_id
        and a.league_season = f.league_season
left join group_snapshot as g
    on
        a.team_id = g.team_id
        and a.league_id = g.league_id
        and a.league_season = g.league_season
inner join placement as p
    on
        a.team_id = p.team_id
        and a.league_id = p.league_id
        and a.league_season = p.league_season
