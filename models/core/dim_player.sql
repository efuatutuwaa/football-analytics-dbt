-- Model: dim_player
-- Grain: 1 row per player (player_id)
-- Materialization: table (football_core) — physical table for fast joins from facts and marts
-- Sources:
--   stg_players — primary; one row per player from raw_players (biographical profile from API)
-- Purpose:
--   Master dimension of players who appear in this project's competitions. Facts and marts
--   join on player_id to add name, nationality, birth details, and photo without repeating
--   attributes from staging or denormalizing player names on every fact row.
-- Player universe (who is in this table):
--   Players are ingested per league_id and season_year via scripts/ingestion/fetch_players.py
--   using LEAGUE_IDS and SEASONS from constants.py — i.e. anyone who appears in squad/player
--   endpoints for the 15 tracked competitions (2020 through current year). Not a global registry
--   of every professional player; a player absent from all ingested league-seasons will not appear.
-- Output columns:
--   player_id       — primary key; join key for player facts, match stats, and marts
--   player_name     — full display name from API (e.g. Erling Haaland)
--   firstname       — given name; may be null
--   lastname        — family name; may be null
--   age             — age at time of API fetch; snapshot only — not updated daily (use birth_date for stable logic)
--   birth_date      — date of birth
--   birth_place     — place of birth string from API
--   birth_country   — country of birth
--   nationality     — nationality string from API (primary country identity for the player)
--   height          — height as returned by API (e.g. "180 cm"); string, not numeric
--   weight          — weight as returned by API (e.g. "75 kg"); string, not numeric
--   photo_url       — headshot image URL for dashboards
--   ingested_at     — last ingest timestamp from stg_players
-- Excludes:
--   Current club or squad — use stg_team_squads or int_player_club_periods (intermediate); marts join dim_club
--   Per-match stats — use fact_player_match_stats (not int_player_match_stats from consumption layer)
--   Season performance — use fact_player_season (aggregated via int_player_season_metrics in intermediate)
--   Club stints — fact_player_club_period; fee-bearing permanents — fact_player_market_value_period
--   Event-level rows — use fact_fixture_events (player_id optional on some events)
-- Design notes:
--   Sourced from staging only — not built from int_player_match_stats or int_player_season_metrics.
--   Those intermediate models are siblings (also from stg_players / stg_player_statistics), not
--   downstream of this dimension. They denormalise player_name on the fact row; dim_player is for
--   enrichment at query time in marts and BI.
--   age is a point-in-time API field — prefer birth_date for age calculations in analysis.
--   nationality is not joined to stg_countries in this dimension; add country_code via left join
--   on nationality = country_name if flag enrichment is needed (same pattern as dim_club).
-- Join targets (consumption layer — do not join int_* for player attributes):
--   fact_player_match_stats, fact_player_season, fact_player_club_period, fact_fixture_events, fact_player_market_value_period
--   Join dim_club on team_id from those facts when club context is required alongside player attributes.

{{ config(materialized='table') }}

select
    -- identifiers
    player_id,
    -- attributes
    player_name,
    firstname,
    lastname,
    age,
    birth_date,
    birth_place,
    birth_country,
    nationality,
    height,
    weight,
    photo_url,
    -- metadata
    ingested_at
from {{ ref('stg_players') }}
