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
        where ingested_at >= (select max(ingested_at) from {{ this }})
    {% endif %}
)

select * from source