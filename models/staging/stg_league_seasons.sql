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
