{{ config(materialized='view') }}

with source as (
    select
        -- identifiers
        player_id,
        -- player details
        trim(player_name) as player_name,
        trim(firstname) as firstname,
        trim(lastname) as lastname,
        age,
        birth_date,
        trim(birth_place) as birth_place,
        trim(birth_country) as birth_country,
        trim(nationality) as nationality,
        trim(height) as height,
        trim(weight) as weight,
        trim(photo_url) as photo_url,
        -- metadata
        cast(ingested_at as timestamp) as ingested_at
    from {{ source('football_raw', 'raw_players') }}
)

select * from source
