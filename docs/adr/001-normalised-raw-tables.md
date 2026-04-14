# ADR 001: Normalised Raw Tables

## Date
2026-04-14

## Status
Accepted

## Context
When designing the raw ingestion layer, I had two options for 
storing API-Football data:

1. Flatten everything into one wide table per endpoint
2. Normalise into separate tables per entity

The API returns deeply nested JSON with multiple distinct entities 
in a single response. For example the fixtures endpoint returns 
fixture metadata, scores, teams, league context and venue data 
all in one response.

## Decision
I chose to normalise raw data into separate tables per entity:

- raw_fixtures — core match metadata
- raw_fixture_scores — halftime, fulltime, extratime scores
- raw_fixture_events — goals, cards, substitutions
- raw_fixture_statistics — team level match stats
- raw_fixture_lineups — formation and coach per match
- raw_fixture_lineup_players — individual player per lineup
- raw_player_statistics — individual player match stats

## Alternatives Considered
**One flat table per endpoint** — simpler ingestion, feIr tables.
Rejected because it mixes concerns, creates very wide tables, 
makes staging transformations harder, and reduces reusability 
across the dbt layer.

## Consequences
- More ingestion scripts to maintain
- Cleaner staging models — each model has one clear source
- Better separation of concerns across the pipeline
- Easier to test and document each entity independently
- More closely mirrors how real AE teams structure raw layers