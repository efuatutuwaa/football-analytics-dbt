-- Model: dim_national_team
-- Grain: 1 row per national team (team_id where is_national_team = true)
-- Materialization: table (football_core) — physical table for fast joins from facts and marts
-- Sources:
--   stg_teams     — primary; one row per team from raw_teams, filtered to national teams only
--   stg_countries — left join on team_country = country_name for ISO code and flag URL
-- Purpose:
--   Master dimension of national teams. Facts and marts join on team_id to add team name, code,
--   country, flag, and logo without repeating attributes from staging or intermediate models.
--   Club sides are excluded — use dim_club for Premier League, La Liga, cups, Champions League,
--   and Club World Cup.
-- Tournament coverage (fixtures and results, not this dimension):
--   league_id 1 — FIFA World Cup
--   league_id 4 — UEFA European Championship
--   Note: AFCON, Copa América, and other confederation tournaments are not in the dataset.
--   Metrics described as "all international football" will be incomplete for many nations.
-- Output columns:
--   team_id            — primary key; join key for fact_national_team_run and related marts
--   team_name          — display name (e.g. Senegal, Netherlands, Brazil)
--   team_code          — short code (e.g. SEN, NED); may be null for some teams
--   team_country       — country the team represents (string from API)
--   team_logo_url      — logo image URL for dashboards
--   country_code       — from stg_countries when team_country matches country_name
--   country_flag_url   — from stg_countries when join succeeds; null if no match
--   ingested_at        — last ingest timestamp from stg_teams
-- Excludes:
--   Club teams (is_national_team = false) — use dim_club
--   team_founded       — omitted; founded year is a club attribute in this project, not used for nations
--   Home venue         — national teams have no permanent stadium in raw_teams; venues are neutral in tournaments
--   Tournament results — use fact_national_team_run (not int_national_team_runs from consumption layer)
--   Competition metadata — use dim_league on league_id (World Cup and Euros only)
-- Design notes:
--   Sourced from staging only, not int_national_team_runs: that model is team × fixture × tournament
--   grain and would omit nations that exist in stg_teams but have no ingested tournament fixtures yet.
--   Country join match rate: if team_country does not exactly match stg_countries.country_name,
--   country_code and country_flag_url will be null while team_country remains populated.
-- Join targets (consumption layer):
--   fact_national_team_run; join fact_fixture on fixture_id for venue and status
--   Join dim_league on league_id for tournament name and type alongside fact rows.
--   Planned mart: mart_national_team_results

{{ config(materialized='table') }}

with national_teams as (
    select
        team_id,
        team_name,
        team_code,
        team_country,
        team_logo_url,
        ingested_at
    from {{ ref('stg_teams') }}
    where is_national_team = true
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
    t.team_logo_url,
    -- country attributes from left join to stg_countries
    c.country_code,
    c.country_flag_url,
    -- metadata
    t.ingested_at
from national_teams as t
left join countries as c
    on t.team_country = c.country_name
