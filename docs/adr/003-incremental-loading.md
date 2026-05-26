# ADR 003: Incremental Loading Strategy

## Date
2026-04-14

## Status
Accepted

## Context
When designing the ingestion layer I had to decide how to handle 
repeated runs of the ingestion scripts. Two options existed:

1. Full refresh — truncate and reload all data on every run
2. Incremental — only fetch and load new or updated data

The project ingests data across 15 competitions, 7 seasons, and 
18 raw tables. A full refresh on every run would:
- Consume excessive API requests (limited to 75,000/day on Pro plan)
- Create unnecessary Databricks compute costs
- Make the pipeline slow and inefficient

## Decision
I chose an incremental loading strategy with a dedicated metadata 
table to track ingestion state:

football_raw.ingestion_metadata
- endpoint STRING
- last_ingested_at TIMESTAMP
- rows_inserted INT
- status STRING
- created_at TIMESTAMP

Each ingestion script:
1. Reads last_ingested_at for its endpoint
2. Fetches only data after that timestamp
3. Loads new records into the raw table
4. Updates last_ingested_at on success
5. Logs status as failed if the run errors

## Alternatives Considered
**Full refresh** — simpler to implement, no metadata table needed.
Rejected because it wastes API quota, increases compute costs,
and is not how production pipelines are designed.

**Watermark in dbt** — handling incrementality in dbt rather than
at ingestion. Rejected because raw data should arrive complete
and correct before dbt transformations begin. Mixing ingestion
logic with transformation logic violates separation of concerns.

## Consequences
- Faster ingestion runs after initial full load
- Reduced API quota consumption
- Reduced Databricks compute costs
- Ingestion metadata table provides an audit trail
- Slightly more complex ingestion scripts
- Initial full load still required for historical data (2020-2025)