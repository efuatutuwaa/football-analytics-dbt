-- Model: mart_club_european_performance
-- Grain: 1 row per club per international club tournament per season (team_id, league_id, league_season)
-- Materialization: table (football_marts) — reporting layer; join dim_club and dim_league in BI
-- Sources (consumption layer only — do not ref int_*):
--   fact_club_intl_run — primary; aggregate finished match rows to campaign grain
--   dim_club           — optional enrich on team_id
--   dim_league         — optional enrich on league_id
-- Purpose:
--   Season-level summary of each club's Champions League or Club World Cup campaign: W/D/L, goals,
--   farthest knockout round, optional group-stage snapshot, and whether they won the tournament.
-- Competitions (league_id):
--   2  — UEFA Champions League
--   15 — FIFA Club World Cup (compare seasons cautiously before/after 2025 format change)
-- Output columns:
--   team_id, team_name, league_id, league_name, league_season
--   matches_played, wins, draws, losses, goals_scored, goals_conceded
--   farthest_round (UEFA-style from league_round_display), farthest_round_order
--   league_round_api — deepest round raw API label (same row as farthest_round when unmapped)
--   group_name, group_position, group_points, group_wins, group_draws, group_losses,
--   group_goals_for, group_goals_against, group_goal_difference — last group-stage row if any
--   was_tournament_winner — true if won the Final on a finished match
--   ingested_at
-- Aggregation logic:
--   Same W/D/L and farthest_round pattern as mart_club_domestic_cup_performance.
--   One row per finished fixture per club (dedupe by fixture_id) so a match is not counted twice
--     if the API emits multiple league_round labels for the same fixture_id.
--   Qualifying / preliminary rounds excluded from matches_played and W/D/L (main tournament only).
--   UCL 2024–25+ league phase = 8 matches; semi-finalist with full knockouts is often 14 total (8+2+2+2).
--   API 'Round of 32' = UEFA 'Knockout round play-offs' (teams ranked 9–24 in UCL league phase).
--   See models/marts/README.md § UCL round labels and macros/normalize_european_club_round.sql.
--   Group columns: latest match in the season where group_name is not null (often UCL group stage).
--   Null group columns in knockout-only rows or when standings were missing for that edition.
-- Excludes:
--   Domestic leagues and cups — fact_club_season, mart_club_domestic_cup_performance
--   National teams — club teams only in fact_club_intl_run
-- SQL patterns: A, B, C, D, E — see models/marts/README.md
-- Design notes:
--   Group snapshot comes from left join to standings at fact build time — not a live group table history.
--   was_tournament_winner requires Final + is_winner; losing finalist has farthest_round = Final but flag false.
-- Consumers:
--   European campaign dashboards, mart_club_honours (european_trophies_won), cross-league matchup analysis

{{ config(materialized='table') }}

-- pattern A: finished European club tournament matches only
with finished_matches as (
    select *
    from {{ ref('fact_club_intl_run') }}
    where match_status_short in ('FT', 'AET', 'PEN')
),

-- dedupe: one row per club per fixture (deepest round label if API duplicates)
deduped_matches as (
    select *
    from finished_matches
    qualify row_number() over (
        partition by team_id, league_id, league_season, fixture_id
        order by round_order desc, match_date desc, fixture_id desc
    ) = 1
),

-- main-tournament rows only (exclude qualifying / preliminary)
tournament_matches as (
    select *
    from deduped_matches
    where
        coalesce(league_round, '') not like '%Qualifying%'
        and coalesce(league_round, '') not like 'Preliminary%'
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
    from tournament_matches
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
        league_round_display as farthest_round,
        league_round as farthest_round_api
    from match_stats
    qualify row_number() over (
        partition by team_id, league_id, league_season
        order by round_order desc, match_date desc, fixture_id desc
    ) = 1
),

-- pattern E: latest group-stage row per campaign — not summed group stats
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
    from tournament_matches
    where group_name is not null
    qualify row_number() over (
        partition by team_id, league_id, league_season
        order by match_date desc, fixture_id desc
    ) = 1
),

final_winners as (
    select
        team_id,
        league_id,
        league_season,
        true as was_tournament_winner
    from deduped_matches
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
    f.farthest_round_api,
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
    coalesce(w.was_tournament_winner, false) as was_tournament_winner,
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
left join final_winners as w
    on
        a.team_id = w.team_id
        and a.league_id = w.league_id
        and a.league_season = w.league_season
