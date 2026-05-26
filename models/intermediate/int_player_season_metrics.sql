-- Model: int_player_season_metrics
-- Grain: 1 row per player per club per league per season (player_id, team_id, league_id, league_season)
--   Mid-season transfers produce separate rows per club.
-- Materialization: table — full refresh aggregate from int_player_match_stats
-- Sources: int_player_match_stats (primary)
-- Purpose:
--   Season totals per player per club per competition — appearances, minutes, goals, assists,
--   cards, pass/tackle/dribble sums, avg_rating (where rating present). Derived in dbt, not API.
-- Aggregations:
--   Group by player_id, team_id, league_id, league_season; sum numeric stats; avg on rating
-- Downstream:
--   fact_player_season, player ranking marts, season-on-season comparisons
-- Excludes: Match-level detail (int_player_match_stats), team-level season stats (int_club_season_metrics)

{{ config(materialized='table') }}

with match_stats as (
    select *
    from {{ ref('int_player_match_stats') }}
),

season_metrics as (
    select
        -- identifiers
        player_id,
        max(player_name) as player_name,
        team_id,
        max(team_name) as team_name,
        league_id,
        max(league_name) as league_name,
        league_season,
        -- season aggregates
        count(*) as appearances,
        sum(case when is_substitute = false then 1 else 0 end) as total_starts,
        sum(minutes_played) as minutes_played,
        sum(total_shots) as total_shots,
        sum(shots_on_target) as shots_on_target,
        sum(goals_scored) as goals,
        sum(assists) as assists,
        sum(yellow_card_count) as yellow_cards,
        sum(red_card_count) as red_cards,
        sum(total_passes) as total_passes,
        sum(total_tackles) as total_tackles,
        sum(interceptions) as interceptions,
        sum(successful_dribbles) as successful_dribbles,
        round(avg(rating), 2) as avg_rating
    from match_stats
    group by
        player_id,
        team_id,
        league_id,
        league_season
)

select * from season_metrics
