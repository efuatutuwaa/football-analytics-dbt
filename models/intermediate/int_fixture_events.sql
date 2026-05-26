-- Model: int_fixture_events
-- Grain: 1 row per in-match event (fixture_id, team_id, player_id, event_type, event_detail,
--        elapsed_minutes, extra_minutes)
-- Materialization: incremental (merge). unique_key matches grain above. Incremental on ingested_at
-- Sources: stg_fixture_events (primary; event_type and event_detail already lowercased)
-- Purpose:
--   Event-level fact with boolean flags so marts filter without repeating CASE logic:
--   is_goal, is_own_goal, is_penalty_goal, is_card, is_yellow_card, is_red_card,
--   is_substitution, is_var_decision
-- Downstream:
--   fact_fixture_events (core passthrough), event-driven marts (goals timeline, cards, subs)
-- Excludes: Aggregated player or team season stats — use int_player_* / int_club_* models
--
-- Known API data quirks:
--   1. 'Missed Penalty' sits under event_type = 'goal' despite not being a goal.
--      is_goal explicitly excludes it: event_type = 'goal' AND event_detail != 'Missed Penalty'.
--   2. VAR event_detail casing was inconsistent in the raw source (e.g. 'Goal cancelled' vs 'Goal Disallowed - Foul').
--      Resolved at staging: stg_fixture_events lowercases both event_type and event_detail.
--      is_var_decision is driven by event_type = 'var' only — event_detail LIKE patterns
--      (is_var_goal_review, is_var_penalty_review, is_var_card_review) work safely on lowercase values.
--   3. 11 VAR rows have a null event_detail. is_var_decision still fires correctly since it
--      only checks event_type.
--   4. Substitutions are numbered (e.g. 'Substitution 1' through 'Substitution 9') representing
--      the substitution batch within a match, not meaningful for classification.
--      is_substitution is driven by event_type = 'subst' only — event_detail is ignored.
--      'Substitution 9' (1 occurrence) is likely a data error or extra-time edge case.
--   5. assist_player_id and assist_player_name are reused by the API across event types:
--      For goals: assist_player = the player who provided the assist.
--      For substitutions: player = player coming OFF, assist_player = player coming ON.
--      Downstream models must filter by event_type before interpreting these fields.
--   6. is_red_card matches event_detail = 'red card' only; second-yellow ('yellow red card') may
--      need a separate flag if required for discipline analysis.

{{ config(
    materialized='incremental',
    unique_key=[
        'fixture_id', 'team_id', 'player_id',
        'event_type', 'event_detail',
        'elapsed_minutes', 'extra_minutes'
    ],
    incremental_strategy='merge'
) }}

with events as (
    select *
    from {{ ref('stg_fixture_events') }}
    {% if is_incremental() %}
        where ingested_at > (select max(ingested_at) from {{ this }})  -- noqa: RF02
    {% endif %}
)

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
    -- event classification
    -- goals
    event_type = 'goal' and event_detail != 'missed penalty' as is_goal,
    event_type = 'goal' and event_detail = 'own goal' as is_own_goal,
    event_type = 'goal' and event_detail = 'penalty' as is_penalty_goal,
    event_type = 'goal' and event_detail = 'missed penalty' as is_missed_penalty,
    -- cards
    event_type = 'card' as is_card,
    event_type = 'card' and event_detail = 'yellow card' as is_yellow_card,
    event_type = 'card' and event_detail = 'red card' as is_red_card,
    -- substitutions
    event_type = 'subst' as is_substitution,
    -- VAR decisions
    event_type = 'var' as is_var_decision,
    event_type = 'var' and event_detail like 'goal%' as is_var_goal_review,
    event_type = 'var' and event_detail like 'penalty%' as is_var_penalty_review,
    event_type = 'var' and event_detail like '%card%' as is_var_card_review,
    event_comments,
    ingested_at
from events
