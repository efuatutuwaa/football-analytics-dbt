-- Model: stg_venues
-- Layer: staging
-- Grain: 1 row per venue_id
-- Materialization: view
-- Source: football_raw.raw_venues
-- Purpose:
--   Stadium and ground reference data (name, city, capacity, surface, image).
--   Feeds dim_venue when implemented; fixture rows also carry inline venue_id/name from stg_fixtures.
-- Transformations:
--   Trims text fields; casts ingested_at to timestamp.
-- Downstream:
--   dim_venue (planned), ad-hoc venue analysis joined via fixture.venue_id
-- Notes:
--   Not all fixtures resolve to a row here — some use venue fields on the fixture record only.

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
    qualify row_number() over (partition by venue_id order by ingested_at desc) = 1
)

select * from source
