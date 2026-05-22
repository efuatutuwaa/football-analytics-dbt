-- Model: stg_team_seasons
-- Layer: staging
-- Grain: 1 row per team_id + league_id + season_year
-- Materialization: view
-- Source: football_raw.raw_team_seasons
-- Purpose:
--   Bridge table: which teams participated in which league-season (all competition types in raw).
--   Foundation for int_club_league_periods after filtering to domestic leagues and clubs.
-- Transformations:
--   Casts ingested_at to timestamp; passes through team_id, league_id, season_year.
-- Downstream:
--   int_club_league_periods (inner join stg_leagues where league_type = 'league', clubs only)
-- Notes:
--   Includes cup and international entries in raw — filter downstream, not at staging.

{{ config(materialized='view') }}

with source as (
    select
        -- identifiers
        team_id,
        league_id,
        season_year,
        -- metadata
        cast(ingested_at as timestamp) as ingested_at
    from {{ source('football_raw', 'raw_team_seasons') }}
)

select * from source
