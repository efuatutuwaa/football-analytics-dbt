-- Model: int_club_league_periods
-- Grain: 1 row per team_id, league_id, season_year
-- Materialization: table — static reference; season participation does not change once ingested
-- Sources: stg_team_seasons (primary), stg_leagues (inner joined on league_id, filtered to
--          league_type = 'league' to exclude cups and tournaments),
--          stg_teams (inner joined on team_id, filtered to is_national_team = false)
-- Purpose:
--   Defines which clubs competed in which domestic leagues per season. The inner joins on
--   league_type and is_national_team ensure cups, international tournaments, and national
--   team entries are excluded. Serves as the club-league-season spine for tracking promotions,
--   relegations, and competition participation. Feeds int_club_season_metrics.

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
