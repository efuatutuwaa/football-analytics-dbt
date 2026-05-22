-- Model: fact_club_match_stats
-- Grain: 1 row per club per fixture (fixture_id, team_id)
-- Materialization: table (football_core) — physical table for match-level club analysis
-- Sources:
--   int_club_matchday_metrics — primary; perspective-normalised fixtures across all competitions
-- Purpose:
--   Core fact for club performance at match grain. Each row is one club's view of one fixture —
--   result, goals, clean sheet, home/away, and team-level match statistics (shots, possession,
--   passes, cards). Join dim_club on team_id and dim_league on league_id in marts or BI.
-- Competitions:
--   All 15 tracked competitions (leagues, domestic cups, UCL, Club World Cup). Filter league_id
--   downstream for league-only, cup-only, or European analysis.
-- Output columns (from int_club_matchday_metrics):
--   fixture_id, league_id, team_id, team_name, team_code, team_country
--   opponent_team_id, opponent_team_name, is_home, is_winner
--   league_name, league_country, league_season, season_start_date, season_end_date, is_current_season
--   league_round, match_date, match_timestamp, first_half_start, second_half_start
--   elapsed_minutes, extra_time, match_duration, match_status_short, match_status_long
--   match_referee, timezone, goals_scored, goals_conceded, team_halftime_score, opponent_halftime_score
--   team_extratime_score, opponent_extratime_score, team_penalty_score, opponent_penalty_score
--   goal_difference, match_result, is_clean_sheet
--   shots_on_goal, shots_off_goal, total_shots, blocked_shots, shots_inside_box, shots_outside_box
--   fouls, corner_kicks, offsides, ball_possession, yellow_cards, red_cards
--   goalkeeper_saves, total_passes, accurate_passes, pass_accuracy, ingested_at
-- Excludes:
--   Season-level league totals — use fact_club_season
--   Domestic cup run progression — use fact_club_domestic_cup_run
--   International club tournament runs — use fact_club_intl_run
--   National teams — club teams only in int_club_matchday_metrics
-- Design notes:
--   Thin exposure layer: perspective flip, match_result, and clean-sheet logic live in intermediate.
--   Each fixture appears twice (home and away rows). Fixture statistics may be null when the API
--   did not return team stats for that match.
--   match_result and is_clean_sheet are null until the fixture is finished. API match_status_short:
--   FT = full time (decided in 90 minutes + stoppage), AET = after extra time (no shootout),
--   PEN = decided on penalty shootout (scores include shootout result where applicable).
-- Consumers (consumption layer):
--   fact_club_season, rolling form marts, ad-hoc match analysis
-- Build path (intermediate only): int_club_season_metrics aggregates int_club_matchday_metrics → fact_club_season.

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
    -- scores and outcomes
    goals_scored,
    goals_conceded,
    team_halftime_score,
    opponent_halftime_score,
    team_extratime_score,
    opponent_extratime_score,
    team_penalty_score,
    opponent_penalty_score,
    goal_difference,
    match_result,
    is_clean_sheet,
    -- match statistics
    shots_on_goal,
    shots_off_goal,
    total_shots,
    blocked_shots,
    shots_inside_box,
    shots_outside_box,
    fouls,
    corner_kicks,
    offsides,
    ball_possession,
    yellow_cards,
    red_cards,
    goalkeeper_saves,
    total_passes,
    accurate_passes,
    pass_accuracy,
    -- metadata
    ingested_at
from {{ ref('int_club_matchday_metrics') }}
