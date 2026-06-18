# Data Architecture & Data Flow

For grains, tradeoffs, and orchestration narrative, see [`case-study.md`](case-study.md) · [`data-catalog.md`](data-catalog.md)

---

## End-to-end flow

```text
┌─────────────────┐     ┌──────────────────────────┐     ┌─────────────────────────────┐
│  API-Football   │     │  Ingestion (Python)       │     │  Databricks Delta           │
│  REST API       │────▶│  scripts/ingestion/*.py   │────▶│  football_raw (19 tables)   │
│  15 competitions│     │  Databricks Jobs DAG      │     │  + ingestion_metadata       │
└─────────────────┘     └──────────────────────────┘     └──────────────┬──────────────┘
                                                                         │
                                                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│  dbt transform (models/)                                                                 │
│                                                                                          │
│  football_staging         football_intermediate      football_core       football_marts  │
│  17 × stg_*       ───▶   14 × int_*        ───▶   5 dim + 12 fact ───▶  18 × mart_*   │
│  (clean / rename)         (business logic)          (star schema)         (reporting)   │
│                                                                                          │
│  snapshots/ ──▶ scd_player_club, scd_club_league   (audit only — dbt snapshot)          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                                                         │
                                                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│  Visualisation & BI  (read mart_* · dim_* · fact_* only — never int_* in dashboards)    │
│                                                                                          │
│   app/ (Streamlit)         looker/ (LookML)            models/semantic/ (MetricFlow)    │
│   8 pages                  8 explores                  reusable metric definitions       │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Layers in one table

| # | Layer | Schema | What it is |
|---|---|---|---|
| 1 | Source | — | API-Football HTTPS |
| 2 | Raw | `football_raw` | Flattened Delta tables from ingestion |
| 3 | Staging | `football_staging` | `stg_*` — typed, renamed, deduped |
| 4 | Intermediate | `football_intermediate` | `int_*` — campaigns, periods (build only, not for BI) |
| 5 | Core | `football_core` | `dim_*`, `fact_*` — star schema |
| 6 | Marts | `football_marts` | `mart_*` — one grain per business question |
| 7 | Apps | `app/`, `looker/`, semantic YAML | Streamlit pages, LookML explores, MetricFlow metrics |

---

## Example: European club page (PSG UCL)

```text
raw_fixtures ──▶ stg_fixtures ──┐
                                 ├──▶ int_club_intl_runs ──▶ fact_club_intl_run ──▶ mart_club_european_performance
raw_fixture_events ──▶ stg_fixture_events ──┘         (UEFA round labels)            (W/D/L, farthest round)
                                                                                             │
dim_club (logo) ─────────────────────────────────────────────────────────────────────────────┼──▶ app/pages/7_european_club.py
```

---

## Orchestration

Both ingestion and dbt transformations run as tasks within the same Databricks Jobs DAG — there is no separate orchestration system.

```text
Databricks Jobs DAG:

  Ingest tasks (12 tasks, serialized — one at a time)
       ↓
  dbt: staging → intermediate → core → marts → ops → semantic
       ↓
  dbt test
       ↓
  dbt snapshot
```

Ingestion tasks run **one at a time** to stay under the API-Football Ultra
per-minute cap (450 req/min). All tasks share the same API key, so parallel
ingest tasks can burst past that limit even when daily quota (75k) is fine.
Job definition: `scripts/ingestion/databricks_job.json`.

For the decision rationale behind Databricks Jobs over Airflow at this stage, see [ADR 007](adr/007-databricks-jobs-over-airflow.md).

---

*football-analytics-dbt · [github.com/efuatutuwaa/football-analytics-dbt](https://github.com/efuatutuwaa/football-analytics-dbt)*
