-- Model: mart_domestic_league_top_scorers
-- Grain: 1 row per player per club per domestic league per season
--        (player_id, team_id, league_id, league_season)
-- Materialization: table (football_marts) — reporting layer; join dim_player in BI
-- Sources (consumption layer only — do not ref int_*):
--   mart_player_season — primary; goals, assists, minutes, per-90 (domestic leagues filtered here)
--   dim_player         — optional enrich on player_id (nationality, photo_url)
-- Purpose:
--   Goal-scorer and assist leaderboards for Europe's tracked domestic leagues (big five only).
--   Not UCL, domestic cups, or national teams — see mart_club_european_performance / mart_world_cup.
--   Ranks each club stint separately (mid-season transfers = two rows in one league-season).
-- Competitions (league_id):
--   39 Premier League (England), 61 Ligue 1 (France), 78 Bundesliga (Germany),
--   135 Serie A (Italy), 140 La Liga (Spain)
-- Output columns:
--   league_id, league_name, league_season
--   goals_rank, assists_rank, goal_contributions_rank — dense_rank within league-season
--   player_id, player_name, nationality, photo_url
--   team_id, team_name
--   appearances, minutes_played, goals, assists, goal_contributions
--   goals_per_90, assists_per_90, goal_contributions_per_90
-- Leaderboard logic:
--   Pattern P — dense_rank() per league_id × league_season; ties share rank (no gaps).
-- Excludes:
--   UEFA competitions, domestic cups, internationals — league_id filter only
--   All-competition player totals — mart_player_season without domestic filter
-- SQL patterns: P — see models/marts/README.md
-- Design notes:
--   Former name mart_top_scorers was too broad; this mart is domestic league only.
--   per_90 from mart_player_season; filter goals > 0 in Streamlit for top-N widgets.
-- Consumers:
--   Streamlit domestic league top-scorers page, big-five season comparisons, player profiles

{{ config(materialized='table') }}

{% set domestic_league_ids = [39, 61, 78, 135, 140] %}

with domestic_stints as (
    select
        player_id,
        player_name,
        team_id,
        team_name,
        league_id,
        league_name,
        league_season,
        appearances,
        minutes_played,
        goals,
        assists,
        goals + assists as goal_contributions,
        goals_per_90,
        assists_per_90,
        round((goals + assists) / nullif(minutes_played / 90.0, 0), 2) as goal_contributions_per_90
    from {{ ref('mart_player_season') }}
    where league_id in ({{ domestic_league_ids | join(', ') }})
),

enriched as (
    select
        s.league_id,
        s.league_name,
        s.league_season,
        s.player_id,
        s.team_id,
        s.player_name,
        s.team_name,
        p.nationality,
        p.photo_url,
        s.appearances,
        s.minutes_played,
        s.goals,
        s.assists,
        s.goal_contributions,
        s.goals_per_90,
        s.assists_per_90,
        s.goal_contributions_per_90
    from domestic_stints as s
    left join {{ ref('dim_player') }} as p
        on s.player_id = p.player_id
)

-- pattern P: dense_rank leaderboards within each league-season (per club stint row)
select
    league_id,
    league_name,
    league_season,
    dense_rank() over (
        partition by league_id, league_season
        order by goals desc, assists desc, player_id asc
    ) as goals_rank,
    dense_rank() over (
        partition by league_id, league_season
        order by assists desc, goals desc, player_id asc
    ) as assists_rank,
    dense_rank() over (
        partition by league_id, league_season
        order by goal_contributions desc, goals desc, player_id asc
    ) as goal_contributions_rank,
    player_id,
    player_name,
    nationality,
    photo_url,
    team_id,
    team_name,
    appearances,
    minutes_played,
    goals,
    assists,
    goal_contributions,
    goals_per_90,
    assists_per_90,
    goal_contributions_per_90
from enriched
