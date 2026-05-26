-- Model: mart_player_matchday
-- Grain: 1 row per player per finished domestic league appearance (fixture_id, player_id)
-- Materialization: table (football_marts) — reporting layer; join dim_player, dim_club, dim_league in BI
-- Sources (consumption layer only — do not ref int_*):
--   fact_player_match_stats — primary; per-match player stats and team perspective result
--   fact_fixture            — join on fixture_id; pattern A finished filter (FT, AET, PEN)
--   dim_player              — optional enrich on player_id
--   dim_club                — optional enrich on team_id
-- Purpose:
--   Match-by-match player timeline for scout views: appearance sequence and rolling last-5
--   goals, assists, goal contributions, minutes, and shots. Partition respects mid-season
--   transfers (separate sequences per player × club × league × season).
-- Competitions (league_id):
--   39 Premier League, 61 Ligue 1, 78 Bundesliga, 135 Serie A, 140 La Liga
-- Output columns:
--   fixture_id, player_id, player_name, team_id, team_name, league_id, league_name, league_season
--   league_round, match_date, is_home, opponent_team_id, opponent_team_name, match_result
--   minutes_played, goals_scored, assists, total_shots, shots_on_target, rating, is_substitute, player_position
--   player_match_number — 1-based sequence within player × team × league × season
--   rolling_goals_last_5, rolling_assists_last_5, rolling_goal_contributions_last_5
--   rolling_minutes_last_5, rolling_shots_last_5
-- Match-level logic:
--   Pattern A — finished fixtures via fact_fixture.match_status_short in (FT, AET, PEN).
--   Pattern K — rolling last-5 partitioned by player_id, team_id, league_id, league_season
--     (current appearance + up to four prior). See models/marts/README.md.
-- Excludes:
--   Season rollups — mart_player_season
--   Club team match stats — mart_club_matchday
--   Cups, Europe, internationals — domestic league_id filter only
--   Unfinished appearances — excluded by pattern A
-- SQL patterns: A, K — see models/marts/README.md
-- Design notes:
--   match_result on fact is the player's team result (win / draw / loss), not individual rating.
--   Rolling windows include the current row; fewer than five rows early in a stint.
--   rating is excluded from rolling avg in v1 (sparse nulls); use per-match rating column.
-- Consumers:
--   Streamlit player scout form chart, match log, portfolio player deep-dive

{{ config(materialized='table') }}

{% set domestic_league_ids = [39, 61, 78, 135, 140] %}

-- pattern A: finished domestic league appearances only
with finished_appearances as (
    select
        p.fixture_id,
        p.player_id,
        p.player_name,
        p.team_id,
        p.team_name,
        p.league_id,
        p.league_name,
        p.league_season,
        p.league_round,
        p.match_date,
        p.is_home,
        p.opponent_team_id,
        p.opponent_team_name,
        p.match_result,
        p.minutes_played,
        p.goals_scored,
        p.assists,
        p.total_shots,
        p.shots_on_target,
        p.rating,
        p.is_substitute,
        p.player_position,
        coalesce(p.goals_scored, 0) + coalesce(p.assists, 0) as goal_contributions
    from {{ ref('fact_player_match_stats') }} as p
    inner join {{ ref('fact_fixture') }} as f
        on p.fixture_id = f.fixture_id
    where
        f.match_status_short in ('FT', 'AET', 'PEN')
        and p.league_id in ({{ domestic_league_ids | join(', ') }})
        and p.match_result is not null
),

sequenced as (
    select
        *,
        row_number() over (
            partition by player_id, team_id, league_id, league_season
            order by match_date, fixture_id
        ) as player_match_number
    from finished_appearances
)

select
    fixture_id,
    player_id,
    player_name,
    team_id,
    team_name,
    league_id,
    league_name,
    league_season,
    league_round,
    match_date,
    is_home,
    opponent_team_id,
    opponent_team_name,
    match_result,
    minutes_played,
    goals_scored,
    assists,
    total_shots,
    shots_on_target,
    rating,
    is_substitute,
    player_position,
    player_match_number,
    -- pattern K: rolling last-5 (current appearance + up to four prior in stint)
    sum(coalesce(goals_scored, 0)) over (
        partition by player_id, team_id, league_id, league_season
        order by match_date, fixture_id
        rows between 4 preceding and current row
    ) as rolling_goals_last_5,
    sum(coalesce(assists, 0)) over (
        partition by player_id, team_id, league_id, league_season
        order by match_date, fixture_id
        rows between 4 preceding and current row
    ) as rolling_assists_last_5,
    sum(goal_contributions) over (
        partition by player_id, team_id, league_id, league_season
        order by match_date, fixture_id
        rows between 4 preceding and current row
    ) as rolling_goal_contributions_last_5,
    sum(coalesce(minutes_played, 0)) over (
        partition by player_id, team_id, league_id, league_season
        order by match_date, fixture_id
        rows between 4 preceding and current row
    ) as rolling_minutes_last_5,
    sum(coalesce(total_shots, 0)) over (
        partition by player_id, team_id, league_id, league_season
        order by match_date, fixture_id
        rows between 4 preceding and current row
    ) as rolling_shots_last_5
from sequenced
