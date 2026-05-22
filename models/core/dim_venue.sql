-- Model: dim_venue
-- Grain: 1 row per stadium / ground (venue_id)
-- Materialization: table (football_core) — physical table for fast joins from facts and marts
-- Sources:
--   stg_venues — primary; deduplicated to the latest ingested row per venue_id
-- Purpose:
--   Master dimension of match venues. Join from fact_fixture on venue_id to add stadium name,
--   city, address, capacity, surface, and image without repeating attributes from staging.
--   fact_fixture already carries venue_name and venue_city from the fixtures API; this dimension
--   enriches consumption queries with slower-changing venue attributes.
-- How venues enter the dataset:
--   raw_venues is populated during team ingestion (scripts/ingestion/fetch_teams.py): each club's
--   API profile includes a nested venue object, which is flattened and appended if venue_id is new.
--   Fixtures (stg_fixtures) also reference venue_id per match. There is no team_id on raw_venues,
--   so this table cannot answer "what is Arsenal's home stadium?" without joining through fixtures.
-- Output columns:
--   venue_id         — primary key; join key from fact_fixture and other match-level facts
--   venue_name       — display name of the stadium or ground
--   venue_city       — city where the venue is located
--   venue_address    — street address from API; may be null
--   venue_capacity   — stated capacity (integer); may be null for smaller or unknown grounds
--   venue_surface    — playing surface (e.g. grass, artificial turf); may be null
--   venue_image_url  — stadium image URL for dashboards
--   ingested_at      — timestamp of the ingest batch that last wrote this venue_id to raw_venues
-- Excludes:
--   Home club assignment — no team_id column; use fact_fixture home_team_id + venue_id per match,
--                          not a permanent club-to-stadium link
--   Match results or attendance — use fact_fixture, fact_club_match_stats, or other facts on fixture_id
--   National-team-only context — many international matches use neutral venues; names on fixtures
--                          may not appear in stg_venues if they were never attached to a club profile
-- Design notes:
--   Sourced from staging only — not built from fact_fixture or int_fixture_spine (siblings at match grain).
--   int_fixture_spine denormalises venue_id per fixture at build time; dim_venue is for enrichment at query time.
--   stg_venues uses qualify row_number() … order by ingested_at desc to keep the latest version of
--   each venue when duplicate venue_id rows exist in raw_venues (append-only ingestion).
--   fixture.venue_id may be null for some rows; left join from facts is appropriate.
--   fixture.venue_name / venue_city on the spine may differ slightly from dim_venue when the fixture
--   API and team API disagree — prefer dim_venue for capacity, surface, and image; spine for match-time label.
-- Join targets (consumption layer):
--   fact_fixture (left join on venue_id for capacity, surface, address, image_url)
--   Marts and BI that need enriched stadium attributes alongside match rows

{{ config(materialized='table') }}

select
    -- identifiers
    venue_id,
    -- attributes
    venue_name,
    venue_city,
    venue_address,
    venue_capacity,
    venue_surface,
    venue_image_url,
    -- metadata
    ingested_at
from {{ ref('stg_venues') }}
