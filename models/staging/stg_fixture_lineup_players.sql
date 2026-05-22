-- Model: stg_fixture_lineup_players
-- Layer: staging
-- Grain: 1 row per player per team per fixture (fixture_id, team_id, player_id)
-- Materialization: incremental (merge). unique_key: fixture_id + team_id + player_id
-- Source: football_raw.raw_fixture_lineup_players
-- Purpose:
--   Starting XI and substitutes with jersey, position, grid coordinates, is_starter flag.
-- Transformations:
--   Trims names; casts is_starter; incremental on ingested_at.
-- Downstream:
--   Lineup / appearance marts (future); join to stg_players on player_id
-- Notes:
--   grid_position is null for substitutes. player_id may not exist in stg_players (warn-level tests).

{{ config(
    materialized='incremental',
    unique_key=[
        'fixture_id', 'team_id', 'player_id'
    ],
    incremental_strategy='merge'
) }}

with source as (
    select
        -- identifiers
        fixture_id,
        team_id,
        player_id,
        -- players
        trim(player_name) as player_name,
        jersey_number,
        position,
        trim(grid_position) as grid_position,
        is_starter,
        -- metadata
        cast(ingested_at as timestamp) as ingested_at
    from {{ source('football_raw', 'raw_fixture_lineup_players') }}
    {% if is_incremental() %}
        where ingested_at > (select max(ingested_at) from {{ this }})
    {% endif %}

)

select * from source
