# Project Documentation

This folder contains technical documentation for the 
Football Analytics dbt Project.

## Architecture overview

**[`architecture.md`](architecture.md)** — ASCII data-flow diagrams from API-Football ingestion through dbt layers to Streamlit, Looker, and MetricFlow. Start here when onboarding or explaining the stack to non-engineers.

**[`football_analytics_story.md`](football_analytics_story.md)** — Portfolio story (Markdown source for [`../portfolio-site/`](../portfolio-site/)). **[`case-study.md`](case-study.md)** — Technical appendix for the portfolio site. **[`data-catalog.md`](data-catalog.md)** — Mart grains, freshness, Streamlit mapping.

## Architecture Decision Records (ADRs)

ADRs document the key architectural decisions made during the 
project, including the context, the decision itself, alternatives 
considered, and the consequences of each choice.

Reading the ADRs gives you a complete picture of why the project 
is built the way it is — not just what was built.

| ADR | Title | Status |
|-----|-------|--------|
| [001](adr/001-normalised-raw-tables.md) | Normalised Raw Tables | Accepted |
| [002](adr/002-delta-tables.md) | Delta Tables in Databricks | Accepted |
| [003](adr/003-incremental-loading.md) | Incremental Loading Strategy | Accepted |
| [004](adr/004-separate-schemas-per-layer.md) | Separate Schemas Per Layer | Accepted |
| [005](adr/005-skipped-team-statistics.md) | Skipped Team Statistics Endpoint | Accepted |
| [006](adr/006-flattened-ingestion-over-raw-json.md) | Flattened Ingestion Over Raw JSON | Accepted |
| [007](adr/007-databricks-jobs-over-airflow.md) | Databricks Jobs Over Airflow | Accepted |
| [008](adr/008-smart-incremental-ingestion.md) | Smart Incremental Ingestion | Accepted |
| [009](adr/009-drop-coach-models-source-data-quality-failure.md) | Drop Coach Models (Source Quality) | Accepted |
| [010](adr/010-transfers-wider-composite-key-and-downstream-tie-breaker.md) | Transfers Wider Composite Key | Accepted |
| [011](adr/011-transfers-as-periods-not-type-2-snapshot.md) | Transfers as Periods, Not Transfer SCD | Accepted |

## Snapshots (Type 2)

dbt snapshots in `snapshots/` → schema `football_core`. **Separate from `dbt run`:**

```bash
dbt snapshot --select scd_player_club scd_club_league
```

| Snapshot | Purpose |
|----------|---------|
| `scd_player_club` | Squad roster changes on re-ingest (audit) |
| `scd_club_league` | Domestic participation corrections (audit) |

**Transfer history** is **`fact_player_club_period`** (periods from transfers), not a snapshot. See ADR 011.

## Marts layer

Reporting models live under `models/marts/`. Each `mart_*.sql` file has a full header (grain, sources, logic).

- **[models/marts/README.md](../models/marts/README.md)** — shared SQL patterns (A–P), including **pattern K** (rolling last-5 form on `mart_club_matchday`: current match + up to four prior in the same league season).

## Consumption (Streamlit, MetricFlow, Looker)

Thin demo slice on six marts — not full coverage of all 18 marts.

| Layer | Path |
|-------|------|
| Streamlit | [`app/README.md`](../app/README.md) |
| dbt Semantic Layer | [`models/semantic/README.md`](../models/semantic/README.md) |
| LookML | [`looker/README.md`](../looker/README.md) |

## Portfolio narrative

Two layers for the interactive portfolio site — story first, specs second:

- **[football_analytics_story.md](football_analytics_story.md)** — human narrative, story chapters, hiring/freelance framing (source for [`../portfolio-site/`](../portfolio-site/))
- **[case-study.md](case-study.md)** — technical appendix aligned with the repository

## Adding a New ADR

When making a significant architectural decision:

1. Create a new file in `adr/` following the naming convention
   `NNN-short-title.md`
2. Use the ADR template below
3. Add the new ADR to the index table above

### ADR Template

```markdown
# ADR NNN: Title

## Date
YYYY-MM-DD

## Status
Accepted | Deprecated | Superseded by ADR NNN

## Context
What situation led to this decision?

## Decision
What did I decide?

## Alternatives Considered
What else did I consider and why was it rejected?

## Consequences
What are the tradeoffs of this decision?
```