-- Model: stg_fixture_statistics
-- Layer: staging
-- Grain: 1 row per team per fixture (fixture_id, team_id) — two rows per match
-- Materialization: incremental (merge). unique_key: fixture_id + team_id
-- Source: football_raw.raw_fixture_statistics
-- Purpose:
--   Team-level match statistics from the API (shots, possession, passes, cards, etc.).
--   One-sided rows joined in int_club_matchday_metrics on fixture_id + team_id.
-- Transformations:
--   Trims team_name; passes through numeric stat columns; ball_possession and pass_accuracy as API strings;
--   incremental on ingested_at.
-- Downstream:
--   int_club_matchday_metrics (left join — null when endpoint not called or data missing for that match)
-- Notes:
--   See docs/adr/005-skipped-team-statistics.md — season team stats are derived in dbt, not ingested.

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
