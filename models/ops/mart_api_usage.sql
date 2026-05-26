-- Model: mart_api_usage
-- Grain: 1 row per calendar day per API endpoint
-- Materialization: table (football_ops) — ops / monitoring layer
-- Sources:
--   football_raw.ingestion_metadata — primary
-- Purpose:
--   Daily API request and row-volume totals by endpoint for quota monitoring
--   (e.g. API-Football plan limits). Roll up in BI for weekly/monthly views.
-- Output columns:
--   run_date, endpoint, total_requests, total_rows_inserted
--   successful_runs, failed_runs
-- Excludes:
--   Per-entity run detail — mart_pipeline_health
-- Design notes:
--   run_date from started_at when present, else last_ingested_at / created_at.
--   requests_used and rows_inserted summed across all runs that day for the endpoint.
-- Consumers:
--   API quota dashboards, cost guardrails, job orchestration reviews

{{ config(materialized='table') }}

select
    cast(coalesce(started_at, last_ingested_at, created_at) as date) as run_date,
    endpoint,
    sum(coalesce(requests_used, 0)) as total_requests,
    sum(coalesce(rows_inserted, 0)) as total_rows_inserted,
    sum(case when status = 'success' then 1 else 0 end) as successful_runs,
    sum(case when status = 'failed' then 1 else 0 end) as failed_runs
from {{ source('football_raw', 'ingestion_metadata') }}
group by
    cast(coalesce(started_at, last_ingested_at, created_at) as date),
    endpoint
