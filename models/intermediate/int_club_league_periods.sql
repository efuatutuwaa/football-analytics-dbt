-- Model: int_club_league_periods
-- Grain: 1 row per club per domestic league per season (team_id, league_id, season_year)
-- Materialization: table — participation reference; full refresh is inexpensive
-- Sources:
--   stg_team_seasons — bridge of team ↔ league-season
--   stg_leagues — inner join; league_type = 'league' (excludes cups and tournaments)
--   stg_teams — inner join; is_national_team = false (clubs only)
-- Purpose:
--   Authoritative list of which clubs competed in which domestic leagues each season.
--   Enriches with league and club attributes for joins without hitting multiple staging tables.
-- Domestic leagues in scope (league_id):
--   39 Premier League, 61 Ligue 1, 78 Bundesliga, 135 Serie A, 140 La Liga
-- Downstream:
--   int_club_season_metrics (inner join restricts matchday metrics to league fixtures only)
--   fact_club_season, mart_club_season, promotion/relegation analysis
-- Excludes: cups (45, 48, 66, 81, 137, 143), UCL/CWC (2, 15), national teams, WC/Euros (1, 4)

{{ config(materialized='table') }}

with leagues as (
    select * from {{ ref('stg_leagues') }}
    where league_type = 'league'
),

team_seasons as (
    select * from {{ ref('stg_team_seasons') }}
),

teams as (
    select * from {{ ref('stg_teams') }}
    where is_national_team = false
)

select
    -- identifiers
    ts.team_id,
    ts.league_id,
    -- season details
    ts.season_year,
    -- league details
    l.league_name,
    l.league_type,
    l.league_country_name,
    l.league_country_code,
    -- team details
    t.team_name,
    t.team_code,
    t.team_country,
    -- metadata
    ts.ingested_at
from team_seasons as ts
inner join leagues as l on ts.league_id = l.league_id
inner join teams as t on ts.team_id = t.team_id
