{{ config(materialized='incremental',
    unique_key=['fixture_id', 'team_id'],
    incremental_strategy='merge'
) }}

with source as (
    select
        -- identifiers
        fixture_id,
        team_id,
        -- team details
        trim(team_name) as team_name,
        -- statistics
        shots_on_goal,
        shots_off_goal,
        total_shots,
        blocked_shots,
        shots_inside_box,
        shots_outside_box,
        fouls,
        corner_kicks,
        offsides,
        trim(ball_possession) as ball_possession,
        yellow_cards,
        red_cards,
        goalkeeper_saves,
        total_passes,
        accurate_passes,
        trim(pass_accuracy) as pass_accuracy,
        -- metadata
        cast(ingested_at as timestamp) as ingested_at
    from {{ source('football_raw', 'raw_fixture_statistics') }}
    {% if is_incremental() %}
        where ingested_at > (select max(ingested_at) from {{ this }})
    {% endif %}
)

select * from source
