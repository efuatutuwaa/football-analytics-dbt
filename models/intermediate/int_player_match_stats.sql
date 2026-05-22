-- Model: int_player_match_stats
-- Grain: 1 row per player per fixture (fixture_id, player_id). unique_key in config matches this.
-- Materialization: incremental (merge). Incremental filter on stg_player_statistics.ingested_at
-- Sources:
--   stg_player_statistics — minutes, goals, assists, passes, cards, rating, etc.
--   int_fixture_spine — left join on fixture_id for league, opponent, dates, home/away, team result
-- Purpose:
--   Player-match fact with competition context so season rollups and marts do not re-join the spine.
--   Carries both raw per-match stats and fixture-level attributes (league_name, match_date, is_home).
-- Downstream:
--   int_player_season_metrics, fact_player_match_stats (core), player performance marts
-- Excludes: Team-level aggregates (int_club_matchday_metrics), event-level rows (int_fixture_events)
-- Notes:
--   A player appears once per fixture per team in source; mid-match team changes are not modelled.

{{ config(
    materialized='incremental',
    unique_key=['fixture_id', 'player_id'],
    incremental_strategy='merge'
) }}

with player_stats as (
    select *
    from {{ ref('stg_player_statistics') }}
    {% if is_incremental() %}
        where ingested_at > (select max(ingested_at) from {{ this }})  -- noqa: RF02
    {% endif %}
),

fixtures as (
    select *
    from {{ ref('int_fixture_spine') }}
),

match_stats as (
    select
        -- identifiers
        ps.fixture_id,
        ps.player_id,
        ps.team_id,
        -- player details
        ps.player_name,
        ps.team_name,
        ps.jersey_number,
        ps.player_position,
        ps.rating,
        ps.is_captain,
        ps.is_substitute,
        -- match context
        f.league_id,
        f.league_name,
        f.league_season,
        f.league_round,
        f.match_date,
        -- home/away context
        ps.team_id = f.home_team_id as is_home,
        -- opponent
        case
            when ps.team_id = f.home_team_id then f.away_team_id
            else f.home_team_id
        end as opponent_team_id,
        case
            when ps.team_id = f.home_team_id then f.away_team_name
            else f.home_team_name
        end as opponent_team_name,
        -- match result from player's team perspective
        case
            when ps.team_id = f.home_team_id and f.is_home_team_winner = true then 'win'
            when ps.team_id = f.home_team_id and f.is_away_team_winner = true then 'loss'
            when ps.team_id = f.away_team_id and f.is_away_team_winner = true then 'win'
            when ps.team_id = f.away_team_id and f.is_home_team_winner = true then 'loss'
            when f.is_home_team_winner is null then null
            else 'draw'
        end as match_result,
        -- statistics
        ps.minutes_played,
        ps.offsides,
        ps.total_shots,
        ps.shots_on_target,
        ps.total_goals_scored as goals_scored,
        ps.total_goals_conceded as goals_conceded,
        ps.assists,
        ps.saves,
        ps.total_passes,
        ps.key_passes,
        ps.pass_accuracy_pct,
        ps.total_tackles,
        ps.blocks,
        ps.interceptions,
        ps.total_duels,
        ps.duels_won,
        ps.dribbles_attempted,
        ps.successful_dribbles,
        ps.dribbles_past,
        ps.fouls_drawn,
        ps.fouls_committed,
        ps.yellow_card_count,
        ps.red_card_count,
        ps.penalties_won,
        ps.penalties_committed,
        ps.penalties_scored,
        ps.penalties_missed,
        ps.penalties_saved,
        -- metadata
        ps.ingested_at
    from player_stats as ps
    left join fixtures as f on ps.fixture_id = f.fixture_id
)

select * from match_stats
qualify row_number() over (
    partition by fixture_id, player_id
    order by ingested_at desc
) = 1
