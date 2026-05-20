-- Model: int_national_team_runs
-- Grain: 1 row per team_id, fixture_id (one row per national team per match)
-- Materialization: incremental (merge) — tournament fixtures accumulate as matches are played
-- Sources: int_fixture_spine (primary, filtered to league_id in (1, 4), qualifying rounds excluded),
--          stg_teams (inner joined on team_id, filtered to is_national_team = true),
--          stg_standings (left joined on league_id + league_season + team_id for group stage record)
-- Competitions: FIFA World Cup (1), UEFA European Championship (4)
-- Purpose:
--   Tracks each national team's progression through international tournaments per edition.
--   Captures group stage record (where applicable) and the farthest knockout round reached.
--   Qualifying rounds are excluded — this model covers the tournament proper only.
--   Note: home/away designation is dropped as most matches are played at neutral venues.
--   Note: coverage is limited to World Cup and Euros only. Metrics scoped to
--   "all international competitions" will be incomplete for non-European nations.

{{ config(
    materialized='incremental',
    unique_key=['fixture_id', 'team_id', 'league_id', 'league_season', 'league_round'],
    incremental_strategy='merge'
) }}

with fixtures as (
    select * from {{ ref('int_fixture_spine') }}
    where
        league_id in (1, 4) -- filter world cup and european championship
        and league_round not like 'Qualifying%' -- exclude qualifying rounds
    {% if is_incremental() %}
        and ingested_at > (select max(ingested_at) from {{ this }})  -- noqa: RF02
    {% endif %}
),

teams as (
    select * from {{ ref('stg_teams') }}
    where is_national_team = true -- filter to national teams only
),

standings as (
    select * from {{ ref('stg_standings') }}
    where league_id in (1, 4) -- world cup and european championship
),

national_team_runs as (
    -- team perspective (home/away dropped since most matches at neutral venues)
    select
        -- identifiers
        f.fixture_id,
        f.league_id,
        f.home_team_id as team_id,
        f.home_team_name as team_name,
        t.team_code,
        t.team_country,
        f.away_team_id as opponent_team_id,
        f.away_team_name as opponent_team_name,
        -- league and season context
        f.league_name,
        f.league_country,
        f.league_season,
        f.season_start_date,
        f.season_end_date,
        f.is_current_season,
        f.league_round,
        -- match timing
        f.match_date,
        f.match_timestamp,
        f.first_half_start,
        f.second_half_start,
        f.elapsed_minutes,
        f.extra_time,
        f.match_duration,
        -- match outcome
        f.is_home_team_winner as is_winner,
        -- match status
        f.match_status_long,
        f.match_status_short,
        f.match_referee,
        f.timezone,
        -- scores
        f.fulltime_home_team_score as goals_scored,
        f.fulltime_away_team_score as goals_conceded,
        f.halftime_home_team_score as team_halftime_score,
        f.halftime_away_team_score as opponent_halftime_score,
        f.extratime_home_team_score as team_extratime_score,
        f.extratime_away_team_score as opponent_extratime_score,
        f.penalty_home_team_score as team_penalty_score,
        f.penalty_away_team_score as opponent_penalty_score,
        -- group stage record (where applicable)
        s.group_name,
        s.team_rank as group_position,
        s.team_points as group_points,
        s.matches_won as group_wins,
        s.matches_drawn as group_draws,
        s.matches_lost as group_losses,
        s.goals_for as group_goals_for,
        s.goals_against as group_goals_against,
        s.goals_difference as group_goal_difference,
        -- metadata
        f.ingested_at
    from fixtures as f
    inner join teams as t on f.home_team_id = t.team_id
    left join standings as s
        on
            f.league_id = s.league_id
            and f.league_season = s.league_season
            and f.home_team_id = s.team_id

    union all

    -- opponent perspective (home/away dropped since most matches at neutral venues)
    select
        -- identifiers
        f.fixture_id,
        f.league_id,
        f.away_team_id as team_id,
        f.away_team_name as team_name,
        t.team_code,
        t.team_country,
        f.home_team_id as opponent_team_id,
        f.home_team_name as opponent_team_name,
        -- league and season context
        f.league_name,
        f.league_country,
        f.league_season,
        f.season_start_date,
        f.season_end_date,
        f.is_current_season,
        f.league_round,
        -- match timing
        f.match_date,
        f.match_timestamp,
        f.first_half_start,
        f.second_half_start,
        f.elapsed_minutes,
        f.extra_time,
        f.match_duration,
        -- match outcome
        f.is_away_team_winner as is_winner,
        -- match status
        f.match_status_long,
        f.match_status_short,
        f.match_referee,
        f.timezone,
        -- scores (invert home/away for opponent perspective)
        f.fulltime_away_team_score as goals_scored,
        f.fulltime_home_team_score as goals_conceded,
        f.halftime_away_team_score as team_halftime_score,
        f.halftime_home_team_score as opponent_halftime_score,
        f.extratime_away_team_score as team_extratime_score,
        f.extratime_home_team_score as opponent_extratime_score,
        f.penalty_away_team_score as team_penalty_score,
        f.penalty_home_team_score as opponent_penalty_score,
        -- group stage record (where applicable)
        s.group_name,
        s.team_rank as group_position,
        s.team_points as group_points,
        s.matches_won as group_wins,
        s.matches_drawn as group_draws,
        s.matches_lost as group_losses,
        s.goals_for as group_goals_for,
        s.goals_against as group_goals_against,
        s.goals_difference as group_goal_difference,
        -- metadata
        f.ingested_at
    from fixtures as f
    inner join teams as t on f.away_team_id = t.team_id
    left join standings as s
        on
            f.league_id = s.league_id
            and f.league_season = s.league_season
            and f.away_team_id = s.team_id
),

round_ordered as (
    select
        *,
        case
            when league_round like 'Group Stage%' then 10
            when league_round like 'Group %' then 10
            when league_round = 'Round of 16' then 20
            when league_round = 'Quarter-finals' then 30
            when league_round = '3rd Place Final' then 35
            when league_round = 'Semi-finals' then 40
            when league_round = 'Final' then 50
            else 0
        end as round_order
    from national_team_runs
)

select
    fixture_id,
    league_id,
    team_id,
    team_name,
    team_code,
    team_country,
    opponent_team_id,
    opponent_team_name,
    league_name,
    league_country,
    league_season,
    season_start_date,
    season_end_date,
    is_current_season,
    league_round,
    round_order,
    round_order = max(round_order) over (
        partition by team_id, league_id, league_season
    ) as is_farthest_round,
    match_date,
    match_timestamp,
    first_half_start,
    second_half_start,
    elapsed_minutes,
    extra_time,
    match_duration,
    is_winner,
    match_status_long,
    match_status_short,
    match_referee,
    timezone,
    goals_scored,
    goals_conceded,
    team_halftime_score,
    opponent_halftime_score,
    team_extratime_score,
    opponent_extratime_score,
    team_penalty_score,
    opponent_penalty_score,
    group_name,
    group_position,
    group_points,
    group_wins,
    group_draws,
    group_losses,
    group_goals_for,
    group_goals_against,
    group_goal_difference,
    ingested_at
from round_ordered
qualify row_number() over (
    partition by fixture_id, team_id, league_id, league_season, league_round
    order by ingested_at desc
) = 1
