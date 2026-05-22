-- Model: int_standings
-- Grain: 1 row per team per league per season per group (league_id, league_season, team_id, group_name)
-- Materialization: table — full refresh; each build reflects latest stg_standings snapshot
-- Sources: stg_standings (primary)
-- Purpose:
--   League table fact with derived win_rate and points_per_game. Preserves home/away splits
--   and promotion/relegation status fields from the API snapshot.
-- Derived fields:
--   win_rate = matches_won / matches_played (3 dp), points_per_game = team_points / matches_played (2 dp)
-- Downstream:
--   fact_standings (core); left join on int_club_intl_runs / int_national_team_runs for group-stage context
-- Notes:
--   Not a matchday history — no round-by-round table in the API. Weekly ingest overwrites via merge at staging.
-- Excludes: Match-level results — use int_fixture_spine or int_club_matchday_metrics

{{ config(materialized='table') }}

with standings as (
    select *
    from {{ ref('stg_standings') }}
),

enriched as (
    select
        -- identifiers
        league_id,
        league_name,
        league_season,
        team_id,
        team_name,
        group_name,
        -- standing position
        team_rank,
        team_points,
        -- overall record
        matches_played,
        matches_won,
        matches_drawn,
        matches_lost,
        goals_for,
        goals_against,
        goals_difference,
        -- home record
        home_matches_played,
        home_matches_won,
        home_matches_drawn,
        home_matches_lost,
        home_goals_for,
        home_goals_against,
        -- away record
        away_matches_played,
        away_matches_won,
        away_matches_drawn,
        away_matches_lost,
        away_goals_for,
        away_goals_against,
        -- derived metrics
        round(matches_won / nullif(matches_played, 0), 3) as win_rate,
        round(team_points / nullif(matches_played, 0), 2) as points_per_game,
        -- form and status
        form,
        standing_status,
        standing_description,
        -- metadata
        last_updated,
        ingested_at
    from standings
)

select * from enriched
