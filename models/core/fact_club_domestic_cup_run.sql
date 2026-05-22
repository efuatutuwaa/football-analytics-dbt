-- Model: fact_club_domestic_cup_run
-- Grain: 1 row per club per fixture per domestic cup (fixture_id, team_id, league_id, league_season, league_round)
-- Materialization: table (football_core) — physical table for cup match analysis and mart aggregation
-- Sources:
--   int_club_domestic_cup_runs — primary; perspective-normalised cup fixtures (two rows per match)
-- Purpose:
--   Core fact for domestic knockout football at match grain. Each row is one club's view of one
--   cup fixture — goals, opponent, home/away, round, and whether that round was the club's
--   farthest progress in that cup and season. Join dim_club on team_id and dim_league on league_id
--   for stable names and competition metadata; use is_farthest_round when building season summaries.
-- Competitions covered (league_id):
--   45  — FA Cup (England)
--   48  — Carabao Cup / EFL Cup (England)
--   66  — Coupe de France
--   81  — DFB-Pokal
--   137 — Coppa Italia
--   143 — Copa del Rey
--   England is the only country with two domestic cups in this dataset.
-- Output columns (from int_club_domestic_cup_runs):
--   fixture_id, league_id, team_id, team_name, team_code, team_country
--   opponent_team_id, opponent_team_name, is_home, is_winner
--   league_name, league_country, league_season, season_start_date, season_end_date, is_current_season
--   league_round, round_order, is_farthest_round
--   match_date, match_timestamp, match_status_short, match_status_long, match_referee, timezone
--   goals_scored, goals_conceded, team_halftime_score, opponent_halftime_score
--   team_extratime_score, opponent_extratime_score, team_penalty_score, opponent_penalty_score
--   ingested_at
-- Excludes:
--   Domestic league standings and season totals — use fact_club_season and fact_standings
--   European club tournaments — use fact_club_intl_run (UCL 2, Club World Cup 15)
--   National teams — club teams only in int_club_domestic_cup_runs
--   Pre-aggregated season campaign metrics — use mart_club_domestic_cup_performance
--                                            (one row per club per cup per season)
-- Design notes:
--   Thin exposure layer over int_club_domestic_cup_runs: business logic (perspective flip, round_order,
--   is_farthest_round) lives in intermediate; this fact is the stable core contract for marts and BI.
--   Each fixture appears twice (home and away team rows); filter or aggregate accordingly.
--   is_farthest_round = true on multiple rows only when the club's exit round had multiple legs/fixtures;
--   for "exit stage" summaries prefer max(round_order) or mart_club_domestic_cup_performance.
--   Replays and two-legged ties may produce more than one row per team per round label — grain tests
--   include fixture_id to keep rows unique.
-- Consumers (consumption layer):
--   mart_club_domestic_cup_performance (season-level cup campaign summary)
--   Ad-hoc analysis: cup runs, giant-killings, home/away cup form, double/treble with fact_club_season

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
    -- metadata
    ingested_at
from {{ ref('int_club_domestic_cup_runs') }}
