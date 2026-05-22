-- Model: stg_league_seasons
-- Layer: staging
-- Grain: 1 row per league_id + season_year
-- Materialization: view
-- Source: football_raw.raw_league_seasons
-- Purpose:
--   Season calendar and API coverage flags per competition edition (start/end dates,
--   is_current_season, which endpoints have data for that league-season).
-- Transformations:
--   Renames coverage_* columns to has_*_coverage booleans used on int_fixture_spine.
-- Downstream:
--   int_fixture_spine (left join on league_id + league_season for season dates and coverage flags)
-- Notes:
--   Coverage flags indicate what the API supports for that edition — not whether this project ingested it.

{{ config(materialized='view') }}

with source as (
    select
        -- identifiers
        league_id,
        -- season details
        season_year,
        season_start as season_start_date,
        season_end as season_end_date,
        is_current_season,
        -- coverage flags
        coverage_fixtures_events as has_fixtures_events_coverage,
        coverage_fixtures_lineups as has_fixtures_lineups_coverage,
        coverage_standings as has_standings_coverage,
        coverage_players as has_players_coverage,
        coverage_top_scorers as has_topscorers_coverage,
        coverage_injuries as has_injuries_coverage,
        coverage_predictions as has_predictions_coverage,
        coverage_odds as has_odds_coverage,
        -- metadata
        cast(ingested_at as timestamp) as ingested_at
    from {{ source('football_raw', 'raw_league_seasons') }}
)

select * from source
