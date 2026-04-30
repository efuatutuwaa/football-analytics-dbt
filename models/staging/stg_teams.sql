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
