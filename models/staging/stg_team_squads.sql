-- Model: stg_team_squads
-- Layer: staging
-- Grain: 1 row per team_id + player_id (current squad roster)
-- Materialization: view
-- Source: football_raw.raw_team_squads
-- Purpose:
--   Point-in-time squad membership per club (jersey, position, age, photo).
--   Refreshed quarterly, weekly during transfer windows in ingestion.
-- Transformations:
--   Trims names; casts ingested_at; passes through roster attributes.
-- Downstream:
--   Squad marts and roster validation (not yet in intermediate layer)
-- Notes:
--   Reflects current squad only — historical membership: int_player_club_periods (no core fact yet).

{{ config(materialized='view') }}

with source as (
    select
        -- identifiers
        team_id,
        player_id,
        -- team
        trim(team_name) as team_name,
        -- player details
        trim(player_name) as player_name,
        player_age,
        jersey_number,
        trim(position) as player_position,
        photo_url,
        -- metadata
        cast(ingested_at as timestamp) as ingested_at
    from {{ source('football_raw', 'raw_team_squads') }}
    qualify row_number() over (partition by team_id, player_id order by ingested_at desc) = 1
)

select * from source
