-- Model: stg_fixture_lineups
-- Layer: staging
-- Grain: 1 row per team per fixture (fixture_id, team_id)
-- Materialization: incremental (merge). unique_key: fixture_id + team_id
-- Source: football_raw.raw_fixture_lineups
-- Purpose:
--   Team formation and coach per match (e.g. 4-3-3). Player-level lineup rows are in stg_fixture_lineup_players.
-- Transformations:
--   Trims formation and coach fields; incremental on ingested_at.
-- Downstream:
--   Lineup marts and analysis (not yet wired through intermediate — available for future models)
-- Notes:
--   Coverage depends on league-season; see stg_league_seasons.has_fixtures_lineups_coverage.

{{ config(materialized='incremental',
    unique_key=['fixture_id', 'team_id'],
    incremental_strategy='merge'
) }}

with source as (
    select
        -- identifiers
        fixture_id,
        team_id,
        coach_id,
        -- team details
        trim(team_name) as team_name,
        trim(coach_name) as coach_name,
        trim(formation) as formation,
        -- metadata
        cast(ingested_at as timestamp) as ingested_at
    from {{ source('football_raw', 'raw_fixture_lineups') }}
    {% if is_incremental() %}
        where ingested_at > (select max(ingested_at) from {{ this }})
    {% endif %}
)

select * from source
