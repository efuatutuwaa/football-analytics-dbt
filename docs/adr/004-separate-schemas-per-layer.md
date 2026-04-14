# ADR 004: Separate Schemas Per Layer

## Date
2026-04-14

## Status
Accepted

## Context
When setting up the Databricks workspace I had to decide how to 
organise the schemas. Two options existed:

1. One schema for everything — all tables in one place
2. Separate schemas per layer — one schema per dbt layer

The project has multiple distinct layers:
- Raw ingestion
- Staging transformations
- Intermediate business logic
- Core dimensions, facts and SCDs
- Marts for reporting

## Decision
I chose separate schemas per layer:

- football_raw — raw ingested data from API-Football
- football_staging — cleaned and renamed staging models
- football_intermediate — business logic and derived fields
- football_core — dimensions, facts and SCD tables
- football_marts — reporting marts for consumption

## Alternatives Considered
**One schema for everything** — simpler setup, fewer schemas to 
manage. Rejected because it mixes raw data with transformed data,
makes it impossible to tell which layer a table belongs to,
and makes access control harder to manage.

**Domain based schemas** — organise by domain rather than layer
e.g. football_players, football_fixtures. Rejected because it
splits related models across schemas and makes lineage harder
to follow.

## Consequences
- Layer is immediately clear from schema name alone
- Access control can be applied per layer if needed
- Mirrors Bolt's production schema conventions
  (stg_models_spark, core_models_spark, mart_models_spark)
- Each future project gets its own schema set
  (lending_raw, lending_staging etc.)
- Slightly more configuration in dbt_project.yml
- Clean separation makes debugging and lineage tracking easier