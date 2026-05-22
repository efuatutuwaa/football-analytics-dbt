-- Model: dim_club
-- Grain: 1 row per club (team_id where is_national_team = false)
-- Materialization: table (football_core) — physical table for fast joins from facts and marts
-- Sources:
--   stg_teams   — primary; one row per team from raw_teams, filtered to clubs only
--   stg_countries — left join on team_country = country_name for ISO code and flag URL
-- Purpose:
--   Master dimension of football clubs across all 15 tracked competitions (domestic leagues,
--   cups, UEFA Champions League, Club World Cup). Facts and marts join on team_id to add
--   club name, short code, country, founded year, and logo without repeating attributes
--   from staging or intermediate models.
-- Output columns:
--   team_id            — primary key; join key for all club facts and marts
--   team_name          — display name (e.g. Arsenal, Real Madrid)
--   team_code          — three-letter code (e.g. ARS, RMA); may be null for some clubs
--   team_country       — country the club is based in (string from API)
--   team_founded       — year founded; sourced from founded_year in stg_teams
--   team_logo_url      — logo image URL for dashboards
--   country_code       — from stg_countries when team_country matches country_name
--   country_flag_url   — from stg_countries when join succeeds; null if no match
--   ingested_at        — last ingest timestamp from stg_teams
-- Excludes:
--   National teams (is_national_team = true) — build dim_national_team separately
--   League/season participation — use fact_club_season (league-only totals; not int_club_league_periods in BI)
--   Home stadium — raw_teams has no venue_id; venues live in stg_venues without team FK
-- Design notes:
--   Sourced from staging only, not int_club_league_periods or other intermediates: those
--   models are team × competition × season grain and filter to specific competition types,
--   so they would drop clubs that exist in stg_teams but never appear in that spine.
-- Join targets (consumption layer — do not join int_* for club attributes):
--   fact_club_match_stats, fact_club_season, fact_club_domestic_cup_run, fact_club_intl_run,
--   fact_player_match_stats, fact_player_season, fact_standings, fact_player_market_value_period
--   Planned marts: mart_club_domestic_cup_performance, mart_club_european_performance, mart_club_season

{{ config(materialized='table') }}

with clubs as (
    select
        team_id,
        team_name,
        team_code,
        team_country,
        team_founded,
        team_logo_url,
        ingested_at
    from {{ ref('stg_teams') }}
    where is_national_team = false
),

countries as (
    select
        country_name,
        country_code,
        country_flag_url
    from {{ ref('stg_countries') }}
)

select
    -- identifiers
    t.team_id,
    -- attributes
    t.team_name,
    t.team_code,
    t.team_country,
    t.team_founded,
    t.team_logo_url,
    -- country attributes from left join to stg_countries
    c.country_code,
    c.country_flag_url,
    -- metadata
    t.ingested_at
from clubs as t
left join countries as c
    on t.team_country = c.country_name
