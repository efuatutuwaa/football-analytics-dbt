-- Model: mart_club_honours
-- Grain: 1 row per club per calendar season with at least one trophy (team_id, league_season)
-- Materialization: table (football_marts) — trophy cabinet and treble/double analysis
-- Sources (consumption layer only — do not ref int_*):
--   fact_standings              — league champions (team_rank = 1 on domestic leagues)
--   fact_club_domestic_cup_run  — domestic cup wins (Final + is_winner)
--   fact_club_intl_run          — UCL / Club World Cup wins (Final + is_winner)
--   dim_club                    — team_name fallback when club won cups but not league title row
-- Purpose:
--   Counts trophies per club per league_season and assigns honour_label (Double, Domestic Treble,
--   Treble) for league-anchored combinations. Answers "did they win the league?", "how many cups?",
--   and treble-style questions without re-unioning facts in every dashboard.
-- Trophy detection:
--   league_titles_won     — fact_standings where league_id in (39, 61, 78, 135, 140) and team_rank = 1
--   domestic_cups_won   — count distinct cup league_ids with a Final win in that season
--   european_trophies_won — count distinct tournament league_ids (2, 15) with a Final win
--   Only finished finals: match_status_short in (FT, AET, PEN). Do not use is_farthest_round alone.
-- Output columns:
--   team_id, team_name, league_season
--   league_titles_won, domestic_cups_won, european_trophies_won, total_trophies
--   honour_label — Treble | Domestic Treble | Double | null
-- honour_label definitions (league title is always the anchor):
--   Treble          — league + 1+ domestic cup + 1+ European trophy
--   Domestic Treble — league + 2+ domestic cups (no European requirement)
--   Double          — league + 1+ domestic cup (no European requirement)
--   null            — every other combination, including league-only or cups/Europe without league
-- Excludes:
--   Seasons with zero trophies — filtered in final WHERE
--   National teams — mart_national_team_honours
--   Match-level detail — underlying facts or campaign marts
-- SQL patterns: C, H, I — see models/marts/README.md
-- Design notes:
--   fact_standings is latest ingest snapshot per league-season — not historical table by round.
--   A club can win two domestic cups in England (FA Cup + Carabao) — both count toward domestic_cups_won.
--   honour_label is null for any club-season that does not match the league-anchored rules above
--   (e.g. league only, two cups without league, league + European but no domestic cup).
-- Consumers:
--   Treble tracker, trophy cabinet viz, join to mart_club_domestic_cup_performance for cup detail

{{ config(materialized='table') }}

with league_titles as (
    select
        team_id,
        max(team_name) as team_name,
        league_season,
        count(*) as league_titles_won
    from {{ ref('fact_standings') }}
    where
        league_id in (39, 61, 78, 135, 140)
        and team_rank = 1
    group by team_id, league_season
),

domestic_cup_wins as (
    select
        team_id,
        league_season,
        count(distinct league_id) as domestic_cups_won
    from {{ ref('fact_club_domestic_cup_run') }}
    where
        league_round = 'Final'
        and is_winner = true
        and match_status_short in ('FT', 'AET', 'PEN')
    group by team_id, league_season
),

european_wins as (
    select
        team_id,
        league_season,
        count(distinct league_id) as european_trophies_won
    from {{ ref('fact_club_intl_run') }}
    where
        league_round = 'Final'
        and is_winner = true
        and match_status_short in ('FT', 'AET', 'PEN')
    group by team_id, league_season
),

-- pattern H: union trophy keys so cup-only or league-only seasons still appear
all_club_seasons as (
    select
        team_id,
        league_season
    from league_titles
    union distinct
    select
        team_id,
        league_season
    from domestic_cup_wins
    union distinct
    select
        team_id,
        league_season
    from european_wins
),

combined as (
    select
        s.team_id,
        coalesce(l.team_name, c.team_name) as team_name,
        s.league_season,
        coalesce(l.league_titles_won, 0) as league_titles_won,
        coalesce(d.domestic_cups_won, 0) as domestic_cups_won,
        coalesce(e.european_trophies_won, 0) as european_trophies_won
    from all_club_seasons as s
    left join league_titles as l
        on
            s.team_id = l.team_id
            and s.league_season = l.league_season
    left join domestic_cup_wins as d
        on
            s.team_id = d.team_id
            and s.league_season = d.league_season
    left join european_wins as e
        on
            s.team_id = e.team_id
            and s.league_season = e.league_season
    left join {{ ref('dim_club') }} as c
        on s.team_id = c.team_id
)

select
    team_id,
    team_name,
    league_season,
    league_titles_won,
    domestic_cups_won,
    european_trophies_won,
    league_titles_won + domestic_cups_won + european_trophies_won as total_trophies,
    case
        when league_titles_won >= 1
             and domestic_cups_won >= 1
             and european_trophies_won >= 1
            then 'Treble'
        when league_titles_won >= 1
             and domestic_cups_won >= 2
            then 'Domestic Treble'
        when league_titles_won >= 1
             and domestic_cups_won >= 1
            then 'Double'
        else null
    end as honour_label
from combined
where league_titles_won + domestic_cups_won + european_trophies_won > 0
