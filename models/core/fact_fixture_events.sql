-- Model: fact_fixture_events
-- Grain: 1 row per in-match event (fixture_id, team_id, player_id, event_type, event_detail,
--        elapsed_minutes, extra_minutes)
-- Materialization: table (football_core) — physical table for event-level analysis
-- Sources:
--   int_fixture_events — primary; boolean flags and API quirks resolved in intermediate
-- Purpose:
--   Core fact for goals, cards, substitutions, and VAR decisions at event grain.
--   Join fact_fixture on fixture_id for competition and match context (league, season, teams, status).
--   Do not join int_fixture_spine from consumption layer — use core facts only.
--   Join dim_club on team_id and dim_player on player_id in marts or Streamlit (left joins — player_id
--   may be null on some events).
-- Output columns (from int_fixture_events):
--   fixture_id, team_id, player_id, assist_player_id, team_name, player_name, assist_player_name
--   elapsed_minutes, extra_minutes, event_type, event_detail, event_comments
--   is_goal, is_own_goal, is_penalty_goal, is_missed_penalty, is_card, is_yellow_card, is_red_card
--   is_substitution, is_var_decision, is_var_goal_review, is_var_penalty_review, is_var_card_review
--   ingested_at
-- Excludes:
--   Match-level team stats — use fact_club_match_stats
--   Season or player aggregates — use fact_player_season
-- Design notes:
--   Thin exposure layer: all CASE logic lives in int_fixture_events (see that model for API quirks).
--   is_goal excludes missed penalties (event_type = 'goal', event_detail = 'missed penalty').
--   On substitutions: player = off, assist_player = on — filter event_type = 'subst' before interpreting.
--   is_red_card matches straight red only; second yellow ('yellow red card') is not flagged today.
--   Intermediate is incremental; this table is a full snapshot built each core run from current int state.
--   Grain unique key includes extra_minutes (null on most rows). dbt_utils uniqueness uses GROUP BY —
--   verify on Databricks that duplicate rows with null extra_minutes are still detected.
-- Consumers (consumption layer):
--   Event timeline marts, goal scorer analysis, discipline dashboards, Streamlit match event explorer

{{ config(materialized='table') }}

select
    -- identifiers
    fixture_id,
    team_id,
    player_id,
    assist_player_id,
    -- players and teams
    team_name,
    player_name,
    assist_player_name,
    -- match timing
    elapsed_minutes,
    extra_minutes,
    -- event raw fields
    event_type,
    event_detail,
    event_comments,
    -- event classification — goals
    is_goal,
    is_own_goal,
    is_penalty_goal,
    is_missed_penalty,
    -- event classification — cards
    is_card,
    is_yellow_card,
    is_red_card,
    -- event classification — substitutions
    is_substitution,
    -- event classification — VAR
    is_var_decision,
    is_var_goal_review,
    is_var_penalty_review,
    is_var_card_review,
    -- metadata
    ingested_at
from {{ ref('int_fixture_events') }}
