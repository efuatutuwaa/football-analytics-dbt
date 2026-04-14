# ADR 006: Flattened Ingestion Over Raw JSON Storage

## Date
2026-04-14

## Status
Accepted

## Context
When designing the ingestion scripts I had to decide how to store 
API-Football responses in the raw layer. Two options existed:

1. Store raw JSON strings — preserve the full nested API response
   as a single STRING column per row
2. Flatten at ingestion — extract and map each field to a 
   dedicated typed column during ingestion

API-Football returns deeply nested JSON responses. For example 
the fixtures/players endpoint nests statistics inside players 
inside teams inside the response array.

## Decision
I chose to flatten the API response at ingestion time, mapping 
each field to a dedicated typed column in the raw table.

For example raw_player_statistics stores:
- goals_scored INT (not nested under goals.total)
- pass_accuracy STRING (not nested under passes.accuracy)
- minutes_played INT (not nested under games.minutes)

## Alternatives Considered
**Store raw JSON strings** — simplest ingestion, no schema 
decisions needed at ingest time. Used by tools like Fivetran 
and Airbyte. Rejected because:
- Requires JSON parsing in every staging model using SQL
- Makes staging models complex and hard to read
- Type casting happens later making raw data harder to inspect
- Harder to write dbt tests against nested JSON columns

**Hybrid approach** — store both raw JSON and flattened columns.
Rejected because it doubles storage and adds complexity without
clear benefit for a single source project.

## Consequences
- Simpler staging models — columns already named and typed
- Raw tables are immediately queryable without JSON parsing
- Schema decisions made once at ingestion time
- If API adds new fields ingestion script must be updated
- More complex ingestion scripts — flatten logic per endpoint
- Follows the principle that staging should be simple:
  SELECT ... FROM ... with light renaming only
- Since I control both ingestion and transformation layers
  flattening at ingestion is the pragmatic choice