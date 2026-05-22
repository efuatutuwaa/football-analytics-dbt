-- Model: stg_players
-- Layer: staging
-- Grain: 1 row per player_id
-- Materialization: view
-- Source: football_raw.raw_players
-- Purpose:
--   Player biographical dimension source (name, age, birth details, nationality, photo).
--   Re-fetched on an annual cadence in ingestion — not match-level.
-- Transformations:
--   Trims player_name; casts birth_date and ingested_at; passes through height/weight as API strings.
-- Downstream (dbt DAG):
--   dim_player; int_player_match_stats → fact_player_match_stats → int_player_season_metrics → fact_player_season
-- Notes:
--   Player_id in match/lineup tables may not always exist here — relationship tests use warn severity.

{{ config(materialized='view') }}

with source as (
    select
        -- identifiers
        player_id,
        -- player details
        trim(player_name) as player_name,
        trim(firstname) as firstname,
        trim(lastname) as lastname,
        age,
        birth_date,
        trim(birth_place) as birth_place,
        trim(birth_country) as birth_country,
        trim(nationality) as nationality,
        trim(height) as height,
        trim(weight) as weight,
        trim(photo_url) as photo_url,
        -- metadata
        cast(ingested_at as timestamp) as ingested_at
    from {{ source('football_raw', 'raw_players') }}
)

select * from source
