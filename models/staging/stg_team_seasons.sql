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
