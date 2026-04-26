{{
    config(
        materialized='table',
        schema='football_ops'
    )
}}

-- mart_pipeline_health
-- Summarises ingestion run outcomes (success / failed / skipped),
-- rows inserted, and runtime minutes derived from started_at →
-- last_ingested_at to support compute-cost monitoring.
-- Write your SQL here.
