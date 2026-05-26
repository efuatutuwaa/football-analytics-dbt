-- Model: mart_national_team_honours
-- Grain: 1 row per national team per tournament edition with a podium finish
--        (team_id, league_id, league_season) — subset of mart_national_team_results
-- Materialization: table (football_marts) — reporting layer for winners and podium dashboards
-- Sources (consumption layer only — do not ref int_*):
--   mart_national_team_results — primary; filter to Winner, Runner-up, Semi-finalist only
--   dim_national_team          — optional enrich on team_id (name, flag, logo)
--   dim_league                 — optional enrich on league_id (tournament name)
-- Purpose:
--   Narrow podium-focused mart for World Cup and European Championship editions. Answers
--   "who won?", "who were the finalists?", and "who reached the semi-finals?" without scanning
--   every nation that exited in the group or Round of 16. Use mart_national_team_results for
--   full edition summaries; mart_world_cup / mart_continental_cups for round-by-round journeys.
-- Competitions (league_id inherited from upstream mart):
--   1 — FIFA World Cup (finals tournament; qualifying excluded upstream)
--   4 — UEFA European Championship (finals tournament)
-- Coverage caveat:
--   Nations only appear when they played in an ingested WC/Euros edition. AFCON, Copa América,
--   and Asian Cup are out of scope for v1 — widen mart_national_team_results filter in v2, then
--   this mart inherits new league_ids with no structural change.
-- Output columns:
--   team_id, team_name, league_id, league_name, league_season
--   tournament_placement — Winner | Runner-up | Semi-finalist (see placement rules below)
--   is_winner, is_runner_up, is_semi_finalist — boolean flags derived from tournament_placement
--   goals_scored, goals_conceded — edition totals from mart_national_team_results (all matches)
--   ingested_at — propagated from upstream mart
-- Placement rules (defined in mart_national_team_results, not re-derived here):
--   Winner         — deepest match is Final and is_winner = true
--   Runner-up      — deepest match is Final and is_winner = false
--   Semi-finalist  — deepest match is Semi-finals and is_winner = false (lost in semi)
--   Not in this mart: Quarter-finalist, Round of 16, Group stage, Eliminated — still in results mart
-- Excludes:
--   Nations without podium finish — filter tournament_placement not in podium set
--   Match-level rows — fact_national_team_run
--   Full campaign metrics (matches_played, wins, group columns) — mart_national_team_results
--   Club honours — mart_club_honours
-- SQL patterns: G (placement from F in mart_national_team_results) — see models/marts/README.md
-- Design notes:
--   Thin filter mart over mart_national_team_results — no new business logic; keeps placement
--   definition in one place (results mart). Re-run results mart before honours when placement CASE changes.
--   Semi-finalist means lost in the semi-final row (deepest round = Semi-finals, not winner), not
--   "reached semis and won" — both semi losers appear; the two finalists are Runner-up + Winner.
--   3rd Place Final / bronze medal matches are not modelled as a separate placement in v1.
--   Join dim_national_team, not dim_club, on team_id.
-- Consumers (consumption layer):
--   Tournament winners timeline, podium counts by nation, portfolio international honours section,
--   drill-down from mart_world_cup (league_id 1) or mart_continental_cups (league_id 4)

{{ config(materialized='table') }}

-- pattern G: filter only — placement logic lives in mart_national_team_results
select
    team_id,
    team_name,
    league_id,
    league_name,
    league_season,
    tournament_placement,
    tournament_placement = 'Winner' as is_winner,
    tournament_placement = 'Runner-up' as is_runner_up,
    tournament_placement = 'Semi-finalist' as is_semi_finalist,
    goals_scored,
    goals_conceded,
    ingested_at
from {{ ref('mart_national_team_results') }}
where tournament_placement in ('Winner', 'Runner-up', 'Semi-finalist')
