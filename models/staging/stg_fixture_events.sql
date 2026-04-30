{{ config(
    materialized='incremental',
    unique_key=[
        'fixture_id', 'team_id', 'player_id',
        'event_type', 'event_detail',
        'elapsed_minutes', 'extra_minutes'
    ],
    incremental_strategy='merge'
) }}

with source as (
    select
        -- identifiers
        fixture_id,
        team_id,
        player_id,
        assist_player_id,
        -- players and teams
        trim(team_name) as team_name,
        trim(player_name) as player_name,
        trim(assist_player_name) as assist_player_name,
        -- match timing
        elapsed_minutes,
        extra_minutes,
        -- event details
        trim(lower(event_type)) as event_type,
        trim(event_detail) as event_detail,
        trim(comments) as event_comments,
        -- metadata
        cast(ingested_at as timestamp) as ingested_at
    from {{ source('football_raw', 'raw_fixture_events') }}
    {% if is_incremental() %}
        where ingested_at > (select max(ingested_at) from {{ this }})
    {% endif %}
)

select * from source