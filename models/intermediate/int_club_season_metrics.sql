-- Model: int_club_season_metrics
-- Grain: 1 row per team_id, league_id, league_season
-- Materialization: table — aggregated from int_club_matchday_metrics
-- Sources: int_club_matchday_metrics (primary), int_club_league_periods (inner joined on
--          team_id + league_id + season_year to restrict to league competitions only)
-- Purpose:
--   Aggregates match-level results into season totals per club per league per season.
--   Captures wins, draws, losses, goals scored/conceded, goal difference, and clean sheets.
--   Scoped to league competitions only — cup and international metrics are tracked separately
--   in int_club_domestic_cup_runs and int_club_intl_runs.
--   Feeds fact_club_season and supports season-on-season performance comparisons downstream.

{{ config(materialized='table') }}

with matchday_metrics as (
    select m.*
    from {{ ref('int_club_matchday_metrics') }} as m
    inner join {{ ref('int_club_league_periods') }} as lp
        on
            m.team_id = lp.team_id
            and m.league_id = lp.league_id
            and m.league_season = lp.season_year  -- restricts to league competitions only
),

season_metrics as (
    select
        -- identifiers
        team_id,
        team_name,
        league_id,
        league_name,
        league_season,
        -- season aggregates
        count(*) as matches_played,
        sum(case when match_result = 'win' then 1 else 0 end) as wins,
        sum(case when match_result = 'draw' then 1 else 0 end) as draws,
        sum(case when match_result = 'loss' then 1 else 0 end) as losses,
        sum(goals_scored) as goals_scored,
        sum(goals_conceded) as goals_conceded,
        sum(goal_difference) as goal_difference,
        sum(case when is_clean_sheet then 1 else 0 end) as clean_sheets
    from matchday_metrics
    group by team_id, team_name, league_id, league_name, league_season
)

select * from season_metrics
