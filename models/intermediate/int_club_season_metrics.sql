-- Model: int_club_season_metrics
-- Grain: 1 row per club per domestic league per season (team_id, league_id, league_season)
-- Materialization: table — full refresh aggregate from match-level source
-- Sources:
--   int_club_matchday_metrics — match results and goals (all competitions in source)
--   int_club_league_periods — inner join on team_id + league_id + league_season = season_year
--     restricts to domestic league fixtures only
-- Purpose:
--   Season totals derived in dbt (not API /teams/statistics) — wins, draws, losses, goals,
--   goal difference, clean sheets. Finished league fixtures only (match_result not null).
-- Aggregations:
--   matches_played = count of finished fixtures (FT/AET/PEN); not scheduled/postponed rows on the calendar.
--   wins/draws/losses sum on match_result; goals and clean_sheets on the same finished rows only.
-- Downstream:
--   fact_club_season, mart_club_season, season-on-season comparisons
-- Excludes: domestic cups (int_club_domestic_cup_runs), European club comps (int_club_intl_runs)
-- Notes: See docs/adr/005-skipped-team-statistics.md for why season stats are derived here.

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
    where match_result is not null
    group by team_id, team_name, league_id, league_name, league_season
)

select * from season_metrics
