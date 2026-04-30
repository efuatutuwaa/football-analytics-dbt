{{ config(
    materialized='incremental',
    unique_key=[
        'fixture_id', 'team_id', 'player_id'
    ],
    incremental_strategy='merge'
) }}

with source as (
    select
        -- identifiers 
        fixture_id,
        team_id,
        player_id,
        -- players
        trim(player_name) as player_name,
        jersey_number,
        position,
        trim(grid_position) as grid_position,
        is_starter,
        -- metadata
        cast(ingested_at as timestamp) as ingested_at
    from {{ source('football_raw', 'raw_fixture_lineup_players') }}
    {% if is_incremental() %}
        where ingested_at > (select max(ingested_at) from {{ this }})
    {% endif %}

)
select * from source