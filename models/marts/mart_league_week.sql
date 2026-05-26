-- Model: mart_league_week
-- Grain: 1 row per domestic league per season per matchweek label
--        (league_id, league_season, league_round)
-- Materialization: table (football_marts) — reporting layer; join dim_league in BI
-- Sources (consumption layer only — do not ref int_*):
--   fact_fixture — primary; one row per fixture; aggregate finished league matches by league_round
--   dim_league   — optional enrich on league_id
-- Purpose:
--   League-wide matchweek summary for calendars and recap dashboards: how many games, goals,
--   home/away/draw split, and date span for each API league_round label (e.g. "Regular Season - 12").
--   Complements mart_league_standings (snapshot table) and mart_club_matchday (club perspective).
-- Competitions (league_id):
--   39 Premier League, 61 Ligue 1, 78 Bundesliga, 135 Serie A, 140 La Liga
-- Output columns:
--   league_id, league_name, league_season, league_round
--   league_week_number — trailing digits parsed from league_round when present (else null)
--   league_week_order — 1-based sequence by earliest match_date in the round (sort key for charts)
--   week_start_date, week_end_date — min / max match_date in the round
--   fixtures_played, total_goals, home_wins, draws, away_wins
--   avg_goals_per_fixture — total_goals / fixtures_played
--   ingested_at — max from underlying fixtures
-- Round-level logic:
--   Pattern A — finished fixtures only: match_status_short in (FT, AET, PEN).
--   Pattern C — max(league_name), max(ingested_at) in GROUP BY; not a business max on names.
-- Excludes:
--   Club perspective — mart_club_matchday (two rows per fixture via fact_club_match_stats)
--   Cups and international — league_id filter to big-five domestic leagues only
--   Unfinished or postponed fixtures — excluded by pattern A
-- SQL patterns: A, C — see models/marts/README.md
-- Design notes:
--   league_round labels are API strings — not normalised across leagues (Matchday vs Regular Season - N).
--   Use league_week_order for chronological charts; league_week_number when regex parse succeeds.
--   W/D/L from is_home_team_winner / is_away_team_winner on fact_fixture (both null on draws).
--   Goals use fulltime scores only (typical for league matches).
-- Consumers:
--   Streamlit league calendar, goals-per-round charts, portfolio league season timeline

{{ config(materialized='table') }}

{% set domestic_league_ids = [39, 61, 78, 135, 140] %}

-- pattern A: finished domestic league fixtures only
with finished_fixtures as (
    select
        fixture_id,
        league_id,
        league_name,
        league_season,
        league_round,
        match_date,
        fulltime_home_team_score,
        fulltime_away_team_score,
        is_home_team_winner,
        is_away_team_winner,
        ingested_at,
        case
            when is_home_team_winner then 'home_win'
            when is_away_team_winner then 'away_win'
            else 'draw'
        end as match_outcome
    from {{ ref('fact_fixture') }}
    where
        league_id in ({{ domestic_league_ids | join(', ') }})
        and match_status_short in ('FT', 'AET', 'PEN')
        and league_round is not null
        and fulltime_home_team_score is not null
        and fulltime_away_team_score is not null
),

round_dates as (
    select
        league_id,
        league_season,
        league_round,
        min(match_date) as week_start_date,
        max(match_date) as week_end_date
    from finished_fixtures
    group by league_id, league_season, league_round
),

round_order as (
    select
        league_id,
        league_season,
        league_round,
        dense_rank() over (
            partition by league_id, league_season
            order by week_start_date, week_end_date, league_round
        ) as league_week_order
    from round_dates
),

-- pattern C: league-wide aggregates per matchweek label
week_agg as (
    select
        f.league_id,
        max(f.league_name) as league_name,
        f.league_season,
        f.league_round,
        try_cast(regexp_extract(f.league_round, '([0-9]+)$', 1) as int) as league_week_number,
        count(*) as fixtures_played,
        sum(f.fulltime_home_team_score + f.fulltime_away_team_score) as total_goals,
        sum(case when f.match_outcome = 'home_win' then 1 else 0 end) as home_wins,
        sum(case when f.match_outcome = 'draw' then 1 else 0 end) as draws,
        sum(case when f.match_outcome = 'away_win' then 1 else 0 end) as away_wins,
        max(f.ingested_at) as ingested_at
    from finished_fixtures as f
    group by f.league_id, f.league_season, f.league_round
)

select
    w.league_id,
    w.league_name,
    w.league_season,
    w.league_round,
    w.league_week_number,
    o.league_week_order,
    d.week_start_date,
    d.week_end_date,
    w.fixtures_played,
    w.total_goals,
    w.home_wins,
    w.draws,
    w.away_wins,
    round(w.total_goals / nullif(w.fixtures_played, 0), 2) as avg_goals_per_fixture,
    w.ingested_at
from week_agg as w
inner join round_dates as d
    on
        w.league_id = d.league_id
        and w.league_season = d.league_season
        and w.league_round = d.league_round
inner join round_order as o
    on
        w.league_id = o.league_id
        and w.league_season = o.league_season
        and w.league_round = o.league_round
