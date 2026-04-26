{{
    config(
        materialized='table',
        schema='football_ops'
    )
}}

-- mart_api_usage
-- Aggregates API request counts from ingestion_metadata to track
-- daily/monthly consumption against the API-Football plan limits.
-- Write your SQL here.
