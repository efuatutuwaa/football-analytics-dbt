# ADR 008: Smart Incremental Ingestion

## Date
2026-05-15

## Status
Accepted

## Context
ADR 003 established the baseline incremental loading strategy: each script
reads `last_ingested_at` from `football_raw.ingestion_metadata`, fetches
only data newer than that timestamp, and updates the watermark on success.

This works well for reference endpoints (leagues, teams, countries, standings)
where data changes infrequently and a time-based watermark is sufficient.

It does not work well for fixture detail endpoints:

- `fetch_fixture_events.py`
- `fetch_fixture_lineups.py`
- `fetch_fixture_statistics.py`
- `fetch_player_statistics.py`

These endpoints return data that only exists once a match has been played.
A pure time-based watermark has two failure modes:

1. **Fetching too early** — if the script runs before a match completes,
   the API returns empty or partial data. The watermark advances and the
   fixture is never re-fetched.

2. **Fetching unnecessarily** — scheduled fixtures that have not yet been
   played are included in the fetch window, consuming API quota for requests
   that return no useful data.

## Decision
Fixture detail scripts use a two-stage filter:

1. **Time filter** — fetch only fixtures where `match_date` falls within
   the recent ingestion window (last N days), consistent with ADR 003.

2. **Status filter** — within that window, only fetch detail data for
   fixtures with a completed status: `FT` (full time), `AET` (after extra
   time), or `PEN` (penalties).

This is implemented by cross-referencing `raw_fixtures.status_short` before
making detail API calls. Fixtures with status `NS` (not started), `1H`, `2H`,
or `HT` are skipped — their detail endpoints will be empty or incomplete.

The fetch window is intentionally set to look back further than one day
(typically 3 days) to catch fixtures that were scheduled but delayed, or
whose status update lagged in the previous run.

## Alternatives Considered
**Fetch all fixtures in the window regardless of status** — simpler, no
cross-reference needed. Rejected because it wastes API quota fetching
empty responses for scheduled fixtures and risks recording partial data
for live matches as complete.

**Event-driven ingestion triggered by status change** — fetch detail data
only when a fixture transitions to FT. Rejected as overly complex for the
current infrastructure. A polling approach with a status filter achieves
the same outcome with less engineering overhead.

## Consequences
- Detail endpoints are never called for fixtures that have not completed
- API quota is preserved for fixtures that actually have data to return
- A 3-day lookback window ensures delayed or rescheduled fixtures are caught
- Adds a dependency on `raw_fixtures.status_short` being up-to-date before
  detail scripts run — `fetch_fixtures.py` must execute first in the job DAG
  (already enforced in the Databricks job orchestration)
- Partial data risk is eliminated for fixture events, lineups, and statistics
