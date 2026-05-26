# Football Analytics — dbt on Databricks

Production-style analytics warehouse for **15 API-Football competitions** (2020–present): Python/PySpark ingestion, layered dbt transformations, a core dimensional model, **18 reporting marts**, and consumption layers (Streamlit, MetricFlow, LookML).

| Read this for… | Document |
|----------------|----------|
| **Architecture flowchart** (ingest → model → viz) | [`docs/architecture.md`](docs/architecture.md) |
| Narrative / portfolio site | [`portfolio-site/`](portfolio-site/) (Next.js) · [Story](docs/football_analytics_story.md) · [Case study](docs/case-study.md) |
| Technical depth (grains, ADRs, counts) | [`docs/case-study.md`](docs/case-study.md) |
| Mart catalogue & shared SQL patterns | [`models/marts/README.md`](models/marts/README.md) |
| Ops marts | [`models/ops/README.md`](models/ops/README.md) |
| MetricFlow | [`models/semantic/README.md`](models/semantic/README.md) |
| Streamlit demo | [`app/README.md`](app/README.md) |
| Looker (review without instance) | [`looker/README.md`](looker/README.md) |

---

## What this repo contains

```text
football-analytics-dbt/
├── docs/architecture.md  → data flow (ASCII): ingest → dbt → Streamlit / Looker / MetricFlow
├── models/
│   ├── staging/          → football_staging
│   ├── intermediate/     → football_intermediate
│   ├── core/             → football_core (dims + facts)
│   ├── marts/            → football_marts (18 tables)
│   ├── ops/              → football_ops
│   └── semantic/         → football_semantic (MetricFlow + time spine)
├── snapshots/            → scd_player_club, scd_club_league
├── macros/               → e.g. parse_transfer_fee_eur
├── scripts/ingestion/    → API-Football → Delta raw
├── app/                  → Streamlit over marts + ops
├── looker/               → LookML explores
└── docs/                 → case study, ADRs, data catalog, portfolio story
```

---

## Warehouse layers

| Layer | Schema | Contents |
|-------|--------|----------|
| Raw | `football_raw` | 19 normalised Delta tables + `ingestion_metadata` |
| Staging | `football_staging` | 17 `stg_*` models |
| Intermediate | `football_intermediate` | 14 `int_*` models (campaign logic, grains) |
| Core | `football_core` | 5 dims + 12 facts |
| **Marts** | **`football_marts`** | **18** `mart_*` reporting tables |
| Ops | `football_ops` | `mart_pipeline_health`, `mart_api_usage` |
| Semantic | `football_semantic` | `time_spine_daily` + MetricFlow YAML |
| Snapshots | `football_core` | `scd_player_club`, `scd_club_league` (audit / Type 2) |

```text
API-Football → Python/PySpark → raw → stg_* → int_* → dim_* / fact_* → mart_*
                                      └→ snapshots/ (scd_player_club, scd_club_league)
```

End-to-end flow (ASCII): **[`docs/architecture.md`](docs/architecture.md)** · Technical depth: **[`docs/case-study.md`](docs/case-study.md)**.

### Consumption rule

Dashboards, Streamlit, Looker, and MetricFlow query **`dim_*`**, **`fact_*`**, and **`mart_*`** — not **`int_*`** or snapshots (except explicit audit use cases).

| Question type | Where to look |
|---------------|---------------|
| Transfer stints | `fact_player_club_period` |
| League participation history | `int_club_league_periods` (build only) |
| Squad / league audit trail | `scd_player_club`, `scd_club_league` |

See [ADR 011](docs/adr/011-transfers-as-periods-not-type-2-snapshot.md).

---

## Marts at a glance (18)

Full grain, sources, and SQL patterns: **[`models/marts/README.md`](models/marts/README.md)**. Per-model spec: comment block at top of each `mart_*.sql`.

| Domain | Models |
|--------|--------|
| **Domestic league** | `mart_club_season`, `mart_player_season`, `mart_club_matchday`, `mart_player_matchday`, `mart_league_week`, `mart_league_standings`, `mart_domestic_league_top_scorers` |
| **Cups & Europe (clubs)** | `mart_club_domestic_cup_performance`, `mart_club_european_performance` (Streamlit + semantic + Looker), `mart_club_honours` |
| **International** | `mart_national_team_results`, `mart_national_team_honours`, `mart_world_cup`, `mart_continental_cups` |
| **Transfers & value** | `mart_transfer_window`, `mart_player_valuation`, `mart_player_value_changes`, `mart_club_squad_value` |

Tests: grain uniqueness in [`models/marts/schema.yml`](models/marts/schema.yml).

**UCL round labels:** API-Football `Round of 32` is mapped to UEFA **Knockout round play-offs** in `mart_club_european_performance` and `fact_club_intl_run` — see [`models/marts/README.md` § UCL round labels](models/marts/README.md#ucl-round-labels-api-football-vs-uefa).

---

## Consumption layers

Same warehouse tables, three paths for demos and reviewers:

| Path | Location | Coverage |
|------|----------|----------|
| **Streamlit** | [`app/`](app/) | Club season (logos), player season (photos), European club, transfers, honours, ops |
| **dbt Semantic Layer** | [`models/semantic/`](models/semantic/) | 7 semantic models, ~21 metrics (`dbt parse` / `dbt sl` if CLI installed) |
| **Looker** | [`looker/`](looker/) | 8 explores (incl. `mart_club_european_performance`) |

Prerequisite for all three: marts built on Databricks (`dbt run --select path:models/marts`).

### Streamlit (quick start)

```bash
cd app
python3 -m venv app-env && source app-env/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Databricks SQL warehouse host, http_path, token
streamlit run streamlit_app.py
```

Details: [`app/README.md`](app/README.md).

---

## Run dbt

**Databricks Jobs:** ingest DAG first, then six dbt tasks (staging → core → marts → ops/semantic → test → snapshot). See **[ADR 007](docs/adr/007-databricks-jobs-over-airflow.md)** and **[`docs/case-study.md` § Architecture](docs/case-study.md)**.

Requires `profiles.yml` for Databricks (not committed). From project root:

```bash
# Build order
dbt run --select path:models/staging path:models/intermediate
dbt run --select path:models/core
dbt run --select path:models/marts
dbt run --select path:models/ops path:models/semantic
dbt snapshot --select scd_player_club scd_club_league

# Tests
dbt test --select path:models/core path:models/marts path:models/ops
```

After changes to farthest-round / cup logic on intermediate models:

```bash
dbt run --select int_club_domestic_cup_runs int_club_intl_runs int_national_team_runs --full-refresh
dbt run --select path:models/marts
```

MetricFlow: `dbt run --select time_spine_daily` once; validate with `dbt parse`. See [`models/semantic/README.md`](models/semantic/README.md).

---

## Ingestion setup

1. Clone repo; install **dbt-databricks** (or adapter you use) and Python deps for `scripts/ingestion/`.
2. Configure **`profiles.yml`** for your catalog/schemas.
3. Create **`scripts/config.py`** with `API_FOOTBALL_KEY` (see `.gitignore` — not committed).
4. Run ingestion scripts / Databricks jobs (orchestration per [ADR 007](docs/adr/007-databricks-jobs-over-airflow.md)).
5. Run dbt build (above), then Streamlit or BI.

Competition IDs: `scripts/ingestion/constants.py`.

---

## Documentation index

- [Architecture Decision Records](docs/README.md)
- [Case study](docs/case-study.md) — grains, layer counts, design tradeoffs
- [Portfolio story](docs/football_analytics_story.md) — human narrative for site copy
- [Marts README](models/marts/README.md) — pattern catalogue (A–P) + model table
- [Ops README](models/ops/README.md)

---

## Out of scope (v1, by design)

- Coach analytics — [ADR 009](docs/adr/009-drop-coach-models-source-data-quality-failure.md)
- API pre-aggregated team season stats — derived in dbt — [ADR 005](docs/adr/005-skipped-team-statistics.md)
- National teams beyond **World Cup (1)** and **Euros (4)** — no AFCON / Copa América in v1
- Full MetricFlow / Looker coverage of all 18 marts — demo slice only

---

## Data & license

Data from [API-Football](https://www.api-football.com/). Respect their terms for public demos and any product use.
