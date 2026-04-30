{{ config(materialized='view') }}

with source as (
    select
        country_name,
        country_code,
        country_flag_url,
        cast(ingested_at as timestamp) as ingested_at
    from {{ source('football_raw', 'raw_countries') }}
)

select * from source
