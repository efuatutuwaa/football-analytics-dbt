-- Model: stg_fixture_events
-- Layer: staging
-- Grain: 1 row per in-match event (unique_key includes fixture, team, player, type, detail, minute)
-- Materialization: incremental (merge)
-- Source: football_raw.raw_fixture_events
-- Purpose:
--   Raw in-match events — goals, cards, substitutions, VAR. Classification flags are added in
--   int_fixture_events, not here.
-- Transformations:
--   Lowercases event_type and event_detail for consistent downstream CASE logic; trims names;
--   incremental on ingested_at.
-- Downstream:
--   int_fixture_events → fact_fixture_events
-- Notes:
--   assist_player_* on substitutions means player ON — see int_fixture_events header for API quirks.
--   'Missed Penalty' arrives with event_type = 'goal' — excluded from is_goal in intermediate.

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
        trim(lower(event_detail)) as event_detail,
        trim(comments) as event_comments,
        -- metadata
        cast(ingested_at as timestamp) as ingested_at
    from {{ source('football_raw', 'raw_fixture_events') }}
    {% if is_incremental() %}
        where ingested_at > (select max(ingested_at) from {{ this }})
    {% endif %}
)

select * from source
