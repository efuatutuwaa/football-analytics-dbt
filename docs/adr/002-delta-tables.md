# ADR 002: Delta Tables in Databricks

## Date
2026-04-14

## Status
Accepted

## Context
When creating raw tables in Databricks I had to choose a table 
format. Databricks supports multiple formats:

1. Delta (default in Databricks)
2. Parquet
3. CSV
4. JSON

The raw layer receives data from repeated ingestion runs and needs 
to support incremental loads, schema evolution, and time travel 
for debugging.

## Decision
I chose Delta format for all raw tables using USING DELTA in 
all DDL statements.

## Alternatives Considered
**Parquet** — widely supported, good performance. Rejected because 
it lacks ACID transactions, time travel, and does not handle 
concurrent writes safely.

**CSV/JSON** — simple but not suitable for a production grade 
warehouse. No schema enforcement, poor query performance, 
no transaction support.

## Consequences
- ACID transactions — concurrent writes are safe
- Time travel — can query data as it was at any point in time.
  Useful for debugging ingestion issues
- Schema evolution — can add columns without breaking existing data
- MERGE support — enables upsert patterns for incremental loading
- Native Databricks optimisation — Delta is the default format
  in Databricks, fully optimised for the platform
- Slightly more storage overhead than plain Parquet — acceptable
  tradeoff for the benefits above