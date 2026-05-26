-- Model: stg_teams
-- Layer: staging
-- Grain: 1 row per team_id (clubs and national teams)
-- Materialization: view
-- Source: football_raw.raw_teams
-- Purpose:
--   Canonical team dimension source — club and national team attributes from the API.
--   is_national_team drives filtering in intermediate models (clubs vs nations).
-- Transformations:
--   Trims team_name, uppercases team_code, casts founded_year and ingested_at.
-- Downstream (dbt DAG):
--   dim_club (is_national_team = false), dim_national_team (= true), intermediate models joining on team_id
-- Notes:
--   Same team_id may appear in multiple competitions; attributes are not competition-specific.

{{ config(materialized='view') }}

with source as (
    select
        -- identifiers
        team_id,
        -- attributes
        trim(team_name) as team_name,
        trim(upper(team_code)) as team_code,
        trim(team_country) as team_country,
        cast(founded_year as int) as team_founded,
        is_national_team,
        team_logo_url,
        -- metadata
        cast(ingested_at as timestamp) as ingested_at
    from {{ source('football_raw', 'raw_teams') }}
)

select * from source
