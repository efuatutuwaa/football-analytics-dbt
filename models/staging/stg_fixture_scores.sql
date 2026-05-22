-- Model: stg_fixture_scores
-- Layer: staging
-- Grain: 1 row per fixture_id
-- Materialization: incremental (merge). unique_key: fixture_id
-- Source: football_raw.raw_fixture_scores
-- Purpose:
--   Period scores (halftime, fulltime, extratime, penalties) joined onto int_fixture_spine.
-- Transformations:
--   Renames home/away columns to halftime_*, fulltime_*, extratime_*, penalty_*; incremental on ingested_at.
-- Downstream:
--   int_fixture_spine (left join — scores null until API publishes them)
-- Notes:
--   extratime_* and penalty_* are null when the match did not go to extra time or shootout.

{{ config(materialized='incremental',
    unique_key=['fixture_id'],
    incremental_strategy='merge'
) }}

with source as (
    select
        -- identifiers
        fixture_id,
        -- scores
        halftime_home as halftime_home_team_score,
        halftime_away as halftime_away_team_score,
        fulltime_home as fulltime_home_team_score,
        fulltime_away as fulltime_away_team_score,
        extratime_home as extratime_home_team_score,
        extratime_away as extratime_away_team_score,
        penalty_home as penalty_home_team_score,
        penalty_away as penalty_away_team_score,
        -- metadata
        cast(ingested_at as timestamp) as ingested_at
    from {{ source('football_raw', 'raw_fixture_scores') }}
    {% if is_incremental() %}
        where ingested_at > (select max(ingested_at) from {{ this }})
    {% endif %}
)

select * from source
