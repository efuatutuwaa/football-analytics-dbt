-- Model: fact_club_intl_run
-- Grain: 1 row per club per fixture per international club tournament
--        (fixture_id, team_id, league_id, league_season, league_round)
-- Materialization: table (football_core) — physical table for European/global club tournament analysis
-- Sources:
--   int_club_intl_runs — primary; perspective-normalised UCL and Club World Cup fixtures (two rows per match)
-- Purpose:
--   Core fact for international club football at match grain. Each row is one club's view of one
--   tournament fixture — goals, opponent, home/away, round, group-stage snapshot (where available),
--   and whether that round was the club's farthest progress in that tournament and season.
--   Join dim_club on team_id and dim_league on league_id in marts or BI for dimension attributes;
--   this fact does not embed those joins (team_name and league_name are already on the row from int).
-- Competitions covered (league_id):
--   2  — UEFA Champions League (group stage + knockout; all seasons in scope)
--   15 — FIFA Club World Cup (format changed significantly in 2025: legacy 7-team vs new 32-team)
-- Output columns (from int_club_intl_runs):
--   fixture_id, league_id, team_id, team_name, team_code, team_country
--   opponent_team_id, opponent_team_name, is_home, is_winner
--   league_name, league_country, league_season, season_start_date, season_end_date, is_current_season
--   league_round, round_order, is_farthest_round
--   match_date, match_timestamp, match_status_short, match_status_long, match_referee, timezone
--   goals_scored, goals_conceded, team_halftime_score, opponent_halftime_score
--   team_extratime_score, opponent_extratime_score, team_penalty_score, opponent_penalty_score
--   group_name, group_position, group_points, group_wins, group_draws, group_losses
--   group_goals_for, group_goals_against, group_goal_difference
--   ingested_at
-- Excludes:
--   Domestic leagues and domestic cups — use fact_club_season and fact_club_domestic_cup_run
--   National teams — club teams only in int_club_intl_runs
--   Season-level campaign summaries — use mart_club_european_performance (one row per club per tournament per season)
-- Design notes:
--   Thin exposure layer over int_club_intl_runs: perspective flip, round_order, is_farthest_round,
--   and group-stage fields from stg_standings live in intermediate; this fact is the stable core contract.
--   Each fixture appears twice (home and away team rows); filter or aggregate accordingly.
--   Group columns come from a left join to stg_standings — populated for group-stage fixtures (mainly UCL;
--   CWC from 2025); null in knockout-only rows or when standings are missing for that edition.
--   is_farthest_round marks rows in the club's deepest round; for exit-stage summaries prefer
--   max(round_order) or mart_club_european_performance.
--   Compare Club World Cup seasons cautiously before/after 2025 — competition structure is not comparable.
-- Consumers (consumption layer):
--   mart_club_european_performance (season-level UCL / CWC campaign summary)
--   Ad-hoc analysis: knockout progression, group-stage exits, cross-league matchups (e.g. Premier League vs La Liga)

{{ config(materialized='table') }}

select
    -- identifiers
    fixture_id,
    league_id,
    team_id,
    -- club
    team_name,
    team_code,
    team_country,
    -- opponent
    opponent_team_id,
    opponent_team_name,
    is_home,
    is_winner,
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
    match_status_short,
    match_status_long,
    match_referee,
    timezone,
    -- scores
    goals_scored,
    goals_conceded,
    team_halftime_score,
    opponent_halftime_score,
    team_extratime_score,
    opponent_extratime_score,
    team_penalty_score,
    opponent_penalty_score,
    -- group stage (from stg_standings via int; null in knockout rounds)
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
from {{ ref('int_club_intl_runs') }}
