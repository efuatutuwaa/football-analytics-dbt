-- Model: dim_league
-- Grain: 1 row per competition (league_id)
-- Materialization: table (football_core) — physical table for fast joins from facts and marts
-- Sources:
--   stg_leagues — primary; one row per competition from raw_leagues (all 15 tracked league_ids)
-- Purpose:
--   Master dimension of competitions in this project. Facts and marts join on league_id to add
--   competition name, type (league / cup / tournament), country, and logo without repeating attributes from
--   staging or denormalizing league names on every fact row.
-- Tracked competitions (see scripts/ingestion/constants.py):
--   league_id 1   — FIFA World Cup (tournament, national teams)
--   league_id 2   — UEFA Champions League (cup, clubs)
--   league_id 4   — UEFA European Championship (tournament, national teams)
--   league_id 15  — FIFA Club World Cup (cup, clubs)
--   league_id 39  — Premier League (league)
--   league_id 45  — FA Cup (cup)
--   league_id 48  — Carabao Cup / EFL Cup (cup)
--   league_id 61  — Ligue 1 (league)
--   league_id 66  — Coupe de France (cup)
--   league_id 78  — Bundesliga (league)
--   league_id 81  — DFB-Pokal (cup)
--   league_id 135 — Serie A (league)
--   league_id 137 — Coppa Italia (cup)
--   league_id 140 — La Liga (league)
--   league_id 143 — Copa del Rey (cup)
-- Output columns:
--   league_id              — primary key; join key for all competition-scoped facts and marts
--   league_name            — display name (e.g. Premier League, UEFA Champions League)
--   league_type            — competition format: 'league', 'cup', or 'tournament' (lowercased at staging)
--   league_country_name    — country the competition is based in (null for some international tournaments)
--   league_country_code    — ISO country code from API
--   league_country_flag_url — flag image URL from API
--   league_logo_url        — competition logo URL for dashboards
--   ingested_at            — last ingest timestamp from stg_leagues
-- Excludes:
--   Season-level metadata — use stg_league_seasons (coverage flags, season start/end dates)
--   Standings — use fact_standings; match context — use fact_fixture; club match rows — fact_club_match_stats
--   Team participation by competition type — fact_club_season (leagues), fact_club_domestic_cup_run (cups),
--                          fact_club_intl_run (UCL/CWC), fact_national_team_run (World Cup/Euros)
-- Design notes:
--   Sourced from staging only, not fixture or standings intermediates: those models are at match or
--   team × season grain and would not improve competition attributes. league_type drives which
--   league_type drives which core fact to use (domestic league vs cup vs international tournament).
--   API league_type values are normalised to lowercase in stg_leagues; use league_id when filtering
--   to a specific competition list is required (e.g. domestic cups only: 45, 48, 66, 81, 137, 143).
-- Join targets (consumption layer):
--   fact_fixture, fact_standings, fact_club_match_stats, fact_club_season, fact_club_domestic_cup_run,
--   fact_club_intl_run, fact_national_team_run, fact_player_match_stats, fact_player_season
--   Planned marts: mart_club_domestic_cup_performance, mart_club_european_performance, mart_national_team_results

{{ config(materialized='table') }}

select
    -- identifiers
    league_id,
    -- attributes
    league_name,
    league_type,
    league_country_name,
    league_country_code,
    league_country_flag_url,
    league_logo_url,
    -- metadata
    ingested_at
from {{ ref('stg_leagues') }}
