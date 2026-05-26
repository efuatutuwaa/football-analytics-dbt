-- Model: stg_fixtures
-- Layer: staging
-- Grain: 1 row per fixture_id
-- Materialization: incremental (merge). unique_key: fixture_id
-- Source: football_raw.raw_fixtures
-- Purpose:
--   Core match schedule and result shell — teams, venue, kick-off, status, league context.
--   Scores live in stg_fixture_scores; team match stats in stg_fixture_statistics.
-- Transformations:
--   Trims text fields; casts dates/timestamps; renames status_* and winner flags; incremental on ingested_at.
-- Downstream:
--   int_fixture_spine (primary parent for almost all match-level intermediate models)
-- Notes:
--   Re-fetched daily for active seasons so status transitions (NS → LIVE → FT) merge into the same row.
--   is_home_team_winner / is_away_team_winner are null on draws and before kick-off.

{{ config(
    materialized='incremental',
    unique_key='fixture_id',
    incremental_strategy='merge'
) }}

with source as (
    select
        -- identifiers
        fixture_id,
        league_id,
        -- league
        trim(league_name) as league_name,
        trim(league_country) as league_country,
        league_season,
        trim(league_round) as league_round,
        -- teams
        home_team_id,
        trim(home_team_name) as home_team_name,
        home_team_winner as is_home_team_winner,
        away_team_id,
        trim(away_team_name) as away_team_name,
        away_team_winner as is_away_team_winner,
        -- venue
        venue_id,
        trim(venue_name) as venue_name,
        trim(venue_city) as venue_city,
        -- match timing
        cast(match_date as date) as match_date,
        cast(match_timestamp as timestamp) as match_timestamp,
        cast(first_period_start as timestamp) as first_half_start,
        cast(second_period_start as timestamp) as second_half_start,
        elapsed_minutes,
        extra_time,
        -- match status
        trim(status_long) as status_long,
        trim(status_short) as status_short,
        -- metadata
        trim(referee) as referee,
        timezone,
        cast(ingested_at as timestamp) as ingested_at
    from {{ source('football_raw', 'raw_fixtures') }}
    {% if is_incremental() %}
        where ingested_at > (select max(ingested_at) from {{ this }})
    {% endif %}
)

select * from source
