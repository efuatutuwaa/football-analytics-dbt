{{ config(materialized='view') }}

with source as (
    select
        -- identifiers
        venue_id,
        -- venue details
        trim(venue_name) as venue_name,
        trim(venue_city) as venue_city,
        trim(venue_address) as venue_address,
        venue_capacity,
        trim(venue_surface) as venue_surface,
        trim(venue_image_url) as venue_image_url,
        -- metadata
        cast(ingested_at as timestamp) as ingested_at
    from {{ source('football_raw', 'raw_venues') }}
)

select * from source
