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