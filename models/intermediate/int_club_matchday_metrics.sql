-- Model: int_club_matchday_metrics
-- Grain: 1 row per club per fixture (fixture_id, team_id). Each match has two rows (home + away).
-- Materialization: incremental (merge). unique_key: fixture_id + team_id.
--   Incremental is safe here — no partition-wide window flags (unlike is_farthest_round models).
-- Sources:
--   int_fixture_spine — match context, scores, status, timing
--   stg_teams — inner join; is_national_team = false (clubs only)
--   stg_fixture_statistics — left join on fixture_id + team_id (null if API omitted stats)
-- Competitions: all 15 tracked league_ids — filter league_id downstream for league / cup / intl
-- Purpose:
--   Club-centric match fact before core. Perspective-normalised columns (goals_scored,
--   goals_conceded, team_halftime_score, etc.) always refer to the club in the row.
-- Business logic:
--   Finished match_status_short values (from API-Football):
--     FT  — full time; outcome decided in regulation (90 minutes + stoppage)
--     AET — after extra time; outcome decided in extra time, no penalty shootout
--     PEN — penalties; outcome decided on shootout (fulltime scores reflect final result)
--   match_result — win / draw / loss only for FT, AET, or PEN; null for NS, LIVE, HT, etc.
--   is_clean_sheet — true when zero goals conceded at full time; null until FT, AET, or PEN
--   goal_difference — goals_scored minus goals_conceded
--   Dedup: qualify row_number() over (fixture_id, team_id) order by ingested_at desc
-- Downstream:
--   fact_club_match_stats (core passthrough)
--   int_club_season_metrics (inner join int_club_league_periods — domestic leagues only)
--   Rolling-form marts and ad-hoc match analysis
-- Excludes: season aggregates, cup run progression, intl runs, national teams, player-level stats

{{ config(
    materialized='incremental',
    unique_key=['team_id', 'fixture_id'],
    incremental_strategy='merge'
) }}

with fixtures as (
    select * from {{ ref('int_fixture_spine') }}
    {% if is_incremental() %}
        where ingested_at > (select max(ingested_at) from {{ this }})  -- noqa: RF02
    {% endif %}
),

teams as (
    select * from {{ ref('stg_teams') }}
    where is_national_team = false -- filter to club teams only
),

fixture_stats as (
    select * from {{ ref('stg_fixture_statistics') }}
    {% if is_incremental() %}
        where ingested_at > (select max(ingested_at) from {{ this }})  -- noqa: RF02
    {% endif %}
),

matchday_metrics as (

    -- home team perspective
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
        true as is_home,
        f.is_home_team_winner as is_winner,
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
        -- match status
        f.match_status_long,
        f.match_status_short,
        f.match_referee,
        f.timezone,
        -- scores and outcomes
        f.fulltime_home_team_score as goals_scored,
        f.fulltime_away_team_score as goals_conceded,
        f.halftime_home_team_score as team_halftime_score,
        f.halftime_away_team_score as opponent_halftime_score,
        f.extratime_home_team_score as team_extratime_score,
        f.extratime_away_team_score as opponent_extratime_score,
        f.penalty_home_team_score as team_penalty_score,
        f.penalty_away_team_score as opponent_penalty_score,
        f.fulltime_home_team_score - f.fulltime_away_team_score as goal_difference,
        case
            when f.match_status_short in ('FT', 'AET', 'PEN') then
                case
                    when f.fulltime_home_team_score > f.fulltime_away_team_score then 'win'
                    when f.fulltime_home_team_score < f.fulltime_away_team_score then 'loss'
                    else 'draw'
                end
        end as match_result,
        case
            when f.match_status_short in ('FT', 'AET', 'PEN')
                then coalesce(f.fulltime_away_team_score = 0, false)
        end as is_clean_sheet,
        -- match statistics (from fixture_stats)
        fs.shots_on_goal,
        fs.shots_off_goal,
        fs.total_shots,
        fs.blocked_shots,
        fs.shots_inside_box,
        fs.shots_outside_box,
        fs.fouls,
        fs.corner_kicks,
        fs.offsides,
        fs.ball_possession,
        fs.yellow_cards,
        fs.red_cards,
        fs.goalkeeper_saves,
        fs.total_passes,
        fs.accurate_passes,
        fs.pass_accuracy,
        -- metadata
        f.ingested_at
    from fixtures as f
    inner join teams as t on f.home_team_id = t.team_id
    left join fixture_stats as fs on f.fixture_id = fs.fixture_id and f.home_team_id = fs.team_id

    union all

    -- away team perspective
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
        false as is_home,
        f.is_away_team_winner as is_winner,
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
        -- match status
        f.match_status_long,
        f.match_status_short,
        f.match_referee,
        f.timezone,
        -- scores and outcomes
        f.fulltime_away_team_score as goals_scored,
        f.fulltime_home_team_score as goals_conceded,
        f.halftime_away_team_score as team_halftime_score,
        f.halftime_home_team_score as opponent_halftime_score,
        f.extratime_away_team_score as team_extratime_score,
        f.extratime_home_team_score as opponent_extratime_score,
        f.penalty_away_team_score as team_penalty_score,
        f.penalty_home_team_score as opponent_penalty_score,
        f.fulltime_away_team_score - f.fulltime_home_team_score as goal_difference,
        case
            when f.match_status_short in ('FT', 'AET', 'PEN') then
                case
                    when f.fulltime_away_team_score > f.fulltime_home_team_score then 'win'
                    when f.fulltime_away_team_score < f.fulltime_home_team_score then 'loss'
                    else 'draw'
                end
        end as match_result,
        case
            when f.match_status_short in ('FT', 'AET', 'PEN')
                then coalesce(f.fulltime_home_team_score = 0, false)
        end as is_clean_sheet,
        -- match statistics (from fixture_stats)
        fs.shots_on_goal,
        fs.shots_off_goal,
        fs.total_shots,
        fs.blocked_shots,
        fs.shots_inside_box,
        fs.shots_outside_box,
        fs.fouls,
        fs.corner_kicks,
        fs.offsides,
        fs.ball_possession,
        fs.yellow_cards,
        fs.red_cards,
        fs.goalkeeper_saves,
        fs.total_passes,
        fs.accurate_passes,
        fs.pass_accuracy,
        -- metadata
        f.ingested_at
    from fixtures as f
    inner join teams as t on f.away_team_id = t.team_id
    left join fixture_stats as fs on f.fixture_id = fs.fixture_id and f.away_team_id = fs.team_id

)

select * from matchday_metrics
qualify row_number() over (
    partition by fixture_id, team_id
    order by ingested_at desc
) = 1
