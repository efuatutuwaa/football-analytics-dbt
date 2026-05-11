{{ config(materialized='view') }}

with source as (
    select
        -- identifiers
        team_id,
        player_id,
        -- team
        trim(team_name) as team_name,
        -- player details
        trim(player_name) as player_name,
        player_age,
        jersey_number,
        trim(position) as player_position,
        photo_url,
        -- metadata
        cast(ingested_at as timestamp) as ingested_at
    from {{ source('football_raw', 'raw_team_squads') }}
    qualify row_number() over (partition by team_id, player_id order by ingested_at desc) = 1
)

select * from source
