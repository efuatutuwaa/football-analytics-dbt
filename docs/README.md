# Project Documentation

This folder contains technical documentation for the 
Football Analytics dbt Project.

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