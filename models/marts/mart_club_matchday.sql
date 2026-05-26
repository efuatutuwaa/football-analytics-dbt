-- Model: mart_club_matchday
-- Grain: 1 row per club per finished domestic league fixture (fixture_id, team_id)
-- Materialization: table (football_marts) — reporting layer; join dim_club and dim_league in BI
-- Sources (consumption layer only — do not ref int_*):
--   fact_club_match_stats — primary; finished league matches with rolling form windows
--   dim_club              — optional enrich on team_id
-- Purpose:
--   Match-by-match domestic league timeline with sequence number and rolling last-5 form metrics
--   (points, goals for/against, wins). Use for form charts and "last N games" widgets in Streamlit.
-- Competitions (league_id):
--   39 Premier League, 61 Ligue 1, 78 Bundesliga, 135 Serie A, 140 La Liga
-- Output columns:
--   fixture_id, team_id, team_name, league_id, league_name, league_season
--   match_date, league_round, is_home, opponent_team_id, opponent_team_name
--   goals_scored, goals_conceded, goal_difference, match_result, is_clean_sheet
--   league_match_number — 1-based sequence within club × league × season (match_date, fixture_id)
--   rolling_points_last_5, rolling_wins_last_5, rolling_goals_scored_last_5, rolling_goals_conceded_last_5
-- Match-level logic:
--   Pattern A — only finished matches: match_status_short in (FT, AET, PEN); match_result not null.
--   Pattern K — rolling last-5: sum(...) over (rows between 4 preceding and current row) ordered by
--     match_date, fixture_id within team_id × league_id × league_season. See models/marts/README.md.
-- Excludes:
--   Cups and European fixtures — filter league_id to big-five domestic leagues only
--   Unfinished matches — excluded by pattern A
--   Season aggregates — mart_club_season
-- SQL patterns: A, K — see models/marts/README.md
-- Design notes:
--   Uses match_result from fact (pre-built in intermediate). Rolling metrics include current match
--   plus up to four prior finished league matches in the same season (rows between 4 preceding and current).
--   Coach context was dropped (ADR 009) — no coach columns in v1.
-- Consumers:
--   Streamlit club form chart, match timeline, portfolio league form section

{{ config(materialized='table') }}

-- pattern A: finished domestic league matches only
with finished_league_matches as (
    select *
    from {{ ref('fact_club_match_stats') }}
    where
        match_status_short in ('FT', 'AET', 'PEN')
        and league_id in (39, 61, 78, 135, 140)
        and match_result is not null
),

sequenced as (
    select
        *,
        row_number() over (
            partition by team_id, league_id, league_season
            order by match_date, fixture_id
        ) as league_match_number,
        case match_result
            when 'win' then 3
            when 'draw' then 1
            else 0
        end as match_points,
        case when match_result = 'win' then 1 else 0 end as is_win
    from finished_league_matches
)

select
    fixture_id,
    team_id,
    team_name,
    league_id,
    league_name,
    league_season,
    match_date,
    league_round,
    is_home,
    opponent_team_id,
    opponent_team_name,
    goals_scored,
    goals_conceded,
    goal_difference,
    match_result,
    is_clean_sheet,
    league_match_number,
    -- pattern K: rolling last-5 (current match + up to four prior in season)
    sum(match_points) over (
        partition by team_id, league_id, league_season
        order by match_date, fixture_id
        rows between 4 preceding and current row
    ) as rolling_points_last_5,
    sum(is_win) over (
        partition by team_id, league_id, league_season
        order by match_date, fixture_id
        rows between 4 preceding and current row
    ) as rolling_wins_last_5,
    sum(goals_scored) over (
        partition by team_id, league_id, league_season
        order by match_date, fixture_id
        rows between 4 preceding and current row
    ) as rolling_goals_scored_last_5,
    sum(goals_conceded) over (
        partition by team_id, league_id, league_season
        order by match_date, fixture_id
        rows between 4 preceding and current row
    ) as rolling_goals_conceded_last_5
from sequenced
