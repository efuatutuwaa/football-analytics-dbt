-- Model: fact_national_team_run
-- Grain: 1 row per national team per fixture (fixture_id, team_id, league_id, league_season, league_round)
-- Materialization: table (football_core) — physical table for World Cup and Euros match-level analysis
-- Sources:
--   int_national_team_runs — primary; perspective-normalised tournament fixtures (two rows per match)
-- Purpose:
--   Core fact for national-team tournament football at match grain. Each row is one nation's view
--   of one finals-tournament fixture — goals, opponent, round, group-stage snapshot (where available),
--   and whether that round was the team's deepest progress in that edition.
--   Join dim_national_team on team_id and dim_league on league_id in marts or BI;
--   join fact_fixture on fixture_id for neutral-site venue and match status without using intermediate.
-- Competitions covered (league_id):
--   1 — FIFA World Cup (tournament proper; qualifying rounds excluded at intermediate)
--   4 — UEFA European Championship (same)
-- Output columns (from int_national_team_runs):
--   fixture_id, league_id, team_id, team_name, team_code, team_country
--   opponent_team_id, opponent_team_name
--   league_name, league_country, league_season, season_start_date, season_end_date, is_current_season
--   league_round, round_order, is_farthest_round
--   match_date, match_timestamp, first_half_start, second_half_start
--   elapsed_minutes, extra_time, match_duration, match_status_short, match_status_long
--   match_referee, timezone, is_winner
--   goals_scored, goals_conceded, team_halftime_score, opponent_halftime_score
--   team_extratime_score, opponent_extratime_score, team_penalty_score, opponent_penalty_score
--   group_name, group_position, group_points, group_wins, group_draws, group_losses
--   group_goals_for, group_goals_against, group_goal_difference, ingested_at
-- Excludes:
--   Qualifying rounds — filtered in int_national_team_runs (league_round not like 'Qualifying%')
--   Clubs, domestic leagues, domestic cups, UCL/CWC — use fact_club_* models
--   is_home — not modelled; most matches are neutral-site (use fact_fixture for venue if needed)
--   AFCON, Copa América, etc. — not in LEAGUE_IDS; "all internationals" metrics will be incomplete
-- Design notes:
--   Thin exposure layer over int_national_team_runs: perspective flip, round_order, is_farthest_round,
--   and group-stage fields from stg_standings live in intermediate; this fact is the stable core contract.
--   Each fixture appears twice (one row per national team). No home/away column by design.
--   is_farthest_round: true on every match in the team's deepest round that edition, not exit-only.
--   For edition summaries (how far did they get), prefer max(round_order) or mart_national_team_results.
--   Group columns are null on knockout-only rows or when standings are missing for that edition.
-- Consumers (consumption layer):
--   mart_national_team_results (season/edition campaign summary)
--   Ad-hoc analysis: knockout runs, group-stage exits, head-to-head in tournaments

{{ config(materialized='table') }}

select
    -- identifiers
    fixture_id,
    league_id,
    team_id,
    -- national team
    team_name,
    team_code,
    team_country,
    -- opponent
    opponent_team_id,
    opponent_team_name,
    -- competition and season
    league_name,
    league_country,
    league_season,
    season_start_date,
    season_end_date,
    is_current_season,
    league_round,
    round_order,
    is_farthest_round,
    -- match timing and status
    match_date,
    match_timestamp,
    first_half_start,
    second_half_start,
    elapsed_minutes,
    extra_time,
    match_duration,
    match_status_short,
    match_status_long,
    match_referee,
    timezone,
    is_winner,
    -- scores
    goals_scored,
    goals_conceded,
    team_halftime_score,
    opponent_halftime_score,
    team_extratime_score,
    opponent_extratime_score,
    team_penalty_score,
    opponent_penalty_score,
    -- group stage (where applicable)
    group_name,
    group_position,
    group_points,
    group_wins,
    group_draws,
    group_losses,
    group_goals_for,
    group_goals_against,
    group_goal_difference,
    -- metadata
    ingested_at
from {{ ref('int_national_team_runs') }}
