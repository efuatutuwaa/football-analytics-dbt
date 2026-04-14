# ADR 007: Databricks Jobs Over Airflow for Orchestration

## Date
2026-04-14

## Status
Accepted

## Context
The ingestion pipeline consists of 13 dependent tasks that must 
run in a specific order. I needed an orchestration tool to:

- Schedule ingestion scripts to run automatically
- Enforce task dependencies (leagues before teams, 
  teams before fixtures etc.)
- Alert on failures
- Provide visibility into pipeline runs

Two main options were considered:

1. Databricks Jobs — native orchestration within Databricks
2. Apache Airflow — industry standard workflow orchestration

## Decision
I chose Databricks Jobs for orchestration in this project.

The full ingestion dependency chain is managed as a single 
Databricks Job with 13 tasks and explicit task dependencies 
ensuring correct execution order:

countries → leagues → teams → coaches → squads → 
players → fixtures → fixture events → fixture statistics → 
fixture lineups → player statistics → transfers → standings

## Alternatives Considered
**Apache Airflow** — industry standard, highly flexible, supports
complex DAGs, widely used in production. Rejected for this project
because:
- Requires additional infrastructure setup (Docker or managed)
- Adds operational overhead for a solo portfolio project
- Databricks Jobs provides sufficient orchestration capability
  for this use case
- Airflow will be introduced in Project 3 (PSP Fintech) where
  cross-platform orchestration is needed

**dbt Cloud Jobs** — can orchestrate dbt runs but cannot 
orchestrate Python ingestion scripts. Rejected because it only 
covers the transformation layer, not the full pipeline.

**GitHub Actions** — already used for CI/CD on PRs. Rejected as
primary orchestration because it is not designed for scheduled
data pipeline runs and lacks task dependency management.

## Consequences
- Simpler setup — Databricks Jobs is native to the platform
- No additional infrastructure required
- Git integration — scripts run directly from GitHub repo
- Task dependencies enforced natively
- Alerting built in via Databricks notifications
- Less flexible than Airflow for complex cross platform pipelines
- Skills gap — Airflow knowledge will be built in Project 3
- Decision can be revisited if orchestration needs grow