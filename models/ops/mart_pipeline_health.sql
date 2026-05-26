-- Model: mart_pipeline_health
-- Grain: 1 row per ingestion_metadata run (endpoint, entity_id, run_started_at)
-- Materialization: table (football_ops) — ops / monitoring layer
-- Sources:
--   football_raw.ingestion_metadata — primary
-- Purpose:
--   Per-run ingestion outcomes: status, rows written, API requests, runtime minutes.
--   Use for job spike checks, failed-run alerts, and compute-cost monitoring.
-- Output columns:
--   run_date, endpoint, entity_id, status, rows_inserted, requests_used
--   started_at, run_started_at, completed_at (last_ingested_at), runtime_minutes
-- Excludes:
--   Raw entity payloads — football_raw.* tables
-- Design notes:
--   run_started_at = coalesce(started_at, last_ingested_at, created_at) — grain key;
--     bulk skipped fixture rows often have null started_at (see fetch_fixture_* scripts).
--   runtime_minutes null when started_at missing (pre-migration metadata rows).
--   Aligns with scripts/job_spike_check.py spike logic.
-- Consumers:
--   Databricks ops dashboards, pipeline alerts, portfolio “platform maturity” section

{{ config(materialized='table') }}

select
    cast(coalesce(started_at, last_ingested_at, created_at) as date) as run_date,
    endpoint,
    entity_id,
    status,
    coalesce(rows_inserted, 0) as rows_inserted,
    coalesce(requests_used, 0) as requests_used,
    started_at,
    coalesce(started_at, last_ingested_at, created_at) as run_started_at,
    last_ingested_at as completed_at,
    case
        when started_at is not null and last_ingested_at is not null
            then round(
                timestampdiff(second, started_at, last_ingested_at) / 60.0,
                2
            )
    end as runtime_minutes
from {{ source('football_raw', 'ingestion_metadata') }}
