-- Model: int_standings
-- Grain: 1 row per team, league, season, and group
-- Materialization: table — standings reflect the latest ingested snapshot
-- Sources: stg_standings (primary)
-- Purpose:
--   Enriches standings data with derived metrics (win_rate, points_per_game) to serve
--   as the foundation for fact_standings. Carries the full home/away split alongside
--   the overall record. Note: stg_standings reflects the latest known state only —
--   no matchday column is available, so this model cannot produce a per-matchday history.

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
