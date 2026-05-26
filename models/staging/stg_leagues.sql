-- Model: stg_leagues
-- Layer: staging
-- Grain: 1 row per competition (league_id)
-- Materialization: view
-- Source: football_raw.raw_leagues
-- Purpose:
--   Master list of the 15 tracked competitions (see scripts/ingestion/constants.py LEAGUE_IDS).
--   Provides league name, type (league/cup/tournament), country, and logo for dims and joins.
-- Transformations:
--   Casts league_id to int; lowercases league_type; renames country fields to league_country_*.
-- Downstream:
--   dim_league, int_club_league_periods (filtered to league_type = 'league'), all competition-scoped facts
-- Notes:
--   Ingestion is scoped to LEAGUE_IDS — rows outside that list should not appear in raw.

{{ config(materialized='view') }}

with source as (
    select
        -- identifiers
        cast(league_id as int) as league_id,
        trim(league_name) as league_name,
        lower(league_type) as league_type,
        -- country
        country_name as league_country_name,
        country_code as league_country_code,
        country_flag_url as league_country_flag_url,
        -- metadata
        league_logo_url,
        cast(ingested_at as timestamp) as ingested_at
    from {{ source('football_raw', 'raw_leagues') }}
)

select * from source
