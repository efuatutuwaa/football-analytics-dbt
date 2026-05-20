# ADR 009: Drop Coach Models - Source Data Quality Failure

## Date
2026-05-15

## Status
Accepted

## Context
Building staging models for the coaches domain (stg_coaches,
stg_coach_careers) revealed systematic data quality failures in the
API-Football /coachs endpoint:

- France and Spain both showed Luis Fuentes as head coach (verified via
  Postman, no transformation involved). One person cannot coach two
  national teams simultaneously — this is a clear data integrity failure
  at source.
- Ghana showed Otto Addo as current head coach despite Ghana's public
  appointment of Carlos Quieroz weeks prior. Verifiable in three minutes
  of Googling. The data was provably stale beyond the API's documented SLA.
- API documentation states the /coachs endpoint refreshes daily. Observed
  data was stale beyond this documented commitment.


## Decision
Drop all coach-related models from the project until source data is
corrected or alternative source is identified:

- ❌ stg_coaches (removed)
- ❌ stg_coach_careers (removed)
- ❌ Planned dim_coach (not built)
- ❌ Planned scd_club_coach (not built)

The raw_coaches and raw_coach_careers tables continue to ingest (the
pipeline doesn't break), but no transformations consume them. The
ingestion scripts remain in the repo as evidence that the infrastructure
exists; they simply produce data that nothing downstream uses.

**Addendum:** The coach ingestion tasks (fetch_coaches.py) were
subsequently removed from the daily Databricks job orchestration to save
compute and API quota. The script and raw tables remain in place;
ingestion is paused. If API data quality improves, ingestion can be
re-enabled with one line in the job YAML.

## Rationale

Bad data ingested silently is worse than no data at all. Building coach
models on demonstrably incorrect source data would:

- Propagate wrongness to all downstream models that join to dim_coach
- Make "current coach" dashboards unreliable
- Make coaching tenure analysis produce authoritative-looking but wrong
  results
- Erode trust in the entire data platform

Dropping the models is preferable to documenting workarounds, because no
transformation can fix data that is wrong at source. Workarounds would
hide the problem; dropping makes the limitation visible.

## Consequences

**Positive:**
- Project ships with no coaching analytics rather than wrong coaching
  analytics
- Source data quality is documented for future review
- Sets a precedent for source-quality-first thinking in this project
- Subsequent decision (ADR 010) cited this as precedent but explicitly
  diverged — domain importance matters when deciding drop vs preserve

**Negative:**
- mart_club_matchday loses planned coach context
- Tactical analysis (formation by coach, coaching style impact) is
  unavailable
- Coaching tenure SCD use case is deferred indefinitely

**Reversible if:**
- API-Football corrects the /coachs endpoint data
- An alternative data source is identified (Transfermarkt scraping,
  manual curation, different API)

## Validation

Source quality verified via direct API call in Postman, isolating the
issue from any ingestion or transformation logic. Specific examples
documented:

- Luis Fuentes returned as coach for both France and Spain (impossible)
- Otto Addo returned as Ghana coach post-appointment of Quieroz (provably
  stale)

## Related

- ADR 005: Skipped Team Statistics Endpoint (precedent for dropping a
  model due to source quality concerns)
- ADR 010: Transfers Composite Key (later decision that *did not* drop
  the domain despite source quality issues, because the data was
  load-bearing and the issue was small — explicit contrast with this ADR)
- Eureka #6 in Story Drafts (narrative version of this decision)
- Data Catalog → Source Limitations section (catalog-level documentation)
