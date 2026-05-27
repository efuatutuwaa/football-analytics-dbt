# Football Analytics Platform — Technical Case Study

A production-style football analytics platform built with Python, PySpark, dbt, and Databricks using real API data.

Built during medical leave ahead of the 2026 World Cup — not as a tutorial exercise, but as a systems-thinking project focused on historical modelling, ingestion architecture, and analytics engineering tradeoffs.


---

## 01 — Overview

### The question that started it

What happens if you build a real football analytics platform from scratch using live API data instead of static datasets?

That sounds like a clean premise. It is not. Football turns out to be an unusually hostile domain for a data modeller, and the hostility is structural, not incidental.

A player can represent both club and country simultaneously. A competition can behave like a round-robin league in one phase and a knockout tournament in the next. Promotions and relegations mean a club's historical context changes every season. Cup competitions quietly distort aggregated statistics if folded into league reporting without discipline. Every one of these is a modelling problem wearing a football shirt.

The further I went, the less this remained a data pipeline project and the more it became a platform architecture problem. That shift — from output-thinking to systems-thinking — is what the rest of this document is actually about.

### Platform at a glance

| Metric | Count |
|---|---|
| Competitions tracked | 15 |
| Players tracked | 41,000+ |
| dbt models | 66 |
| Seasons covered | 2020 → present |
| Staging models | 17 |
| Intermediate models | 14 |
| Fact tables | 12 |
| Reporting marts | 18 |

### Stack

| Layer | Technology |
|---|---|
| Ingestion | Python + PySpark |
| Storage | Databricks Delta Lake |
| Transformation | dbt Core |
| Warehouse | Databricks |
| Visualisation | Streamlit |
| BI modelling | LookML |
| Semantic layer | MetricFlow |
| CI | GitHub Actions |
| Orchestration | Databricks Jobs |

---

## 02 — Architecture

### How the platform is structured

The platform follows a layered medallion-style architecture, with each layer having a precisely defined responsibility. The most important early decision was keeping those responsibilities clean — no logic bleeding across layers.

```
API-Football → Python + PySpark → Delta Lake → dbt layers → Marts → Consumption
```

### Layer responsibilities

| Layer | Purpose | Technology |
|---|---|---|
| Ingestion | Fetch, flatten, and land structured data from API | Python + PySpark |
| Storage | Typed Delta tables with incremental merge support | Databricks Delta Lake |
| `stg_*` | Cleaning, type casting, standardisation — no business logic | dbt |
| `int_*` | Business logic, entity resolution, period modelling | dbt |
| `dim_*` / `fact_*` | Current-state dimensions and analytical event models | dbt |
| `mart_*` | Reporting and BI consumption — grain-specific aggregates | dbt |
| Semantic layer | Reusable metrics, consistent business definitions | MetricFlow |
| Visualisation | Interactive analytical UI | Streamlit + LookML |

### Orchestration

Ingestion and dbt transformations are both orchestrated via Databricks Jobs DAG — there is no separate orchestration system. The full pipeline runs as a single DAG:

```
Databricks Jobs DAG:

  Ingest tasks (7 leaf tasks, parallel)
       ↓
  dbt: staging → intermediate → core → marts → ops → semantic
       ↓
  dbt test
       ↓
  dbt snapshot
```

The full pipeline — ingestion across 15 competitions, 66 dbt models across 6 transformation layers, tests, and snapshots — completes in **32 minutes 46 seconds** end to end. Ingestion alone accounts for approximately 23 minutes; the entire dbt stack adds only 9 minutes on top.

A future migration to Airflow or Dagster would give finer-grained dependency control and better failure isolation across the ingestion-to-transformation boundary.

### Architectural decision — raw layer design

**The question:** flatten nested JSON during ingestion, or land raw payloads first?

**Chosen — flatten at ingestion.** Typed Delta tables immediately. Cleaner dbt staging. Simpler downstream modelling. Easier debugging in the early phase when iteration speed mattered most.

**Deferred — bronze-layer approach.** Replayability, looser extraction coupling, safer schema evolution, cleaner separation between extraction and transformation. The right long-term architecture — not the right starting point.

> Good architecture is not free architecture. It is tradeoffs you understand well enough to defend later. The bronze-layer approach belongs in the "what I'd build next" list precisely because the cost of deferring it is now visible.

---

## 03 — Ingestion

### Incremental architecture and a 20-hour lesson

The ingestion layer uses metadata-driven incremental logic. Before hitting the API, ingestion freshness is checked, unnecessary fetches are skipped, and only relevant entities are processed. This reduced duplicate ingestion, wasted API quota, and unnecessary compute from the first week.

But the most important ingestion lesson did not come from architecture. It came from one particularly slow weekend.

---

### Incident: The Weekend Job

Early in the platform build, the transfer ingestion script was written to fetch transfer histories for every player in the database. At the time, that meant more than 16,000 players — including thousands who had never made a meaningful senior appearance.

The job ran. Nothing broke. After nearly a full weekend of compute, it completed.

**Before:**

| Metric | Value |
|---|---|
| Runtime | ~20 hours |
| Players fetched | 16,000+ |
| Operationally relevant | Most were not |

The problem was not the code. The problem was the question the code was answering. The script was fetching everybody instead of asking: *who actually matters operationally?*

Filtering to active players with meaningful appearances resolved it.

**After:**

| Metric | Value |
|---|---|
| Runtime | ~1 minute |
| Player filter | Active only |
| Analytical value | Identical |

> Systems become fast when the question becomes precise. The architecture was never the bottleneck. The question was.

---

The API quota sits at 75,000 requests per day — a number that sounds large until competitions expand, historical seasons grow, and fetch logic contains even one inefficient loop. Precision in the question is the cheapest form of performance optimisation.

### Raw layer structure

The raw layer is normalised by entity:

- `raw_teams`
- `raw_team_seasons`
- `raw_players`
- `raw_transfers`
- `raw_fixtures`
- `raw_fixture_events`
- `raw_player_statistics`

One of the first major corrections came after Manchester United appeared nine times in a single teams table. The issue was conceptual: club identity and club participation are not the same thing. Conflating them breaks every downstream model that touches both.

---

## 04 — Scale

### When the numbers grew, what actually happened

Expanding from 9 competitions to 15 produced a runtime increase that initially looked alarming — until the underlying player volume change was measured alongside it.

**Ingestion runtime:**

| Scope | Runtime |
|---|---|
| 9 competitions | 12 minutes |
| 15 competitions | 23 minutes |

**Player volume:**

| Scope | Players |
|---|---|
| 9 competitions | ~16,000 |
| 15 competitions | ~41,000 |

Runtime grew 1.9×. Player volume grew 2.6×. The runtime scaling was sub-linear relative to data growth. That is a healthy system.

Domestic cup competitions were the main driver of volume growth — lower-division squads introduce significant additional player records that do not appear in top-flight league data. Without the earlier runtime benchmark, this would have looked like a platform problem. It was the opposite.

> Benchmarks are not optional. Without a baseline, a healthy system and a broken one produce the same initial reaction: why is this slow? The number that matters is not the absolute runtime — it is whether growth is linear, sub-linear, or exponential relative to the data being processed.

---

## 05 — Modelling

### Historical truth requires explicit design

The most architecturally significant decision in the dbt layer was not which models to build — it was how to separate current state from historical participation. Overwriting dimensions answers questions about the present. It destroys the ability to answer questions about the past.

| Concern | Approach | Example |
|---|---|---|
| Current state | Type 1 dimensions — overwrite on change | `dim_player`, `dim_club`, `dim_league` |
| Historical periods | Explicit period modelling via fact tables | `fact_player_club_period` |
| Audit + reingestion | dbt snapshots for change tracking | `scd_player_club`, `scd_club_league` |

The period modelling approach — rather than relying entirely on Type 2 SCD snapshots — means that questions like *"which club did Mbappé belong to during a specific date range?"* or *"which league was Burnley playing in during the 2022/23 season?"* are answerable without scanning snapshot history tables. The grain is explicit. The join is clean.

> "Which league was Burnley playing in during that season?" requires historical modelling, not an overwritten dimension. The design choice that answers that question correctly costs something upfront and saves everything downstream.

Snapshots exist primarily for audit and data quality visibility, not as the primary vehicle for historical analysis. Using snapshots as the main analytical path adds complexity at query time for a problem that explicit period modelling handles better at model definition time.

---

## 06 — Domain Knowledge

### Personal fandom is not domain expertise

At one point in the build, there was a nearly-complete reporting mart that blended Premier League matches, domestic cup fixtures, and European games into a single set of aggregated club statistics. The SQL worked. The metrics were wrong.

Cup competitions distort what look like clean league statistics in ways that are easy to overlook and hard to detect once they're in production. Consider a concrete example: a club's Premier League win rate across a full season might sit at 68%. Fold in FA Cup fixtures — where Premier League sides routinely face Championship and League One opposition — and that rate appears to rise to 73%. The metric has become analytically misleading. A top-tier club's performance is now being evaluated partly against lower-division opponents, producing a false impression of dominance that evaporates the moment anyone checks the underlying fixtures.

> Points-per-match, scoring averages, and clean-sheet rates all break in the same direction when competition types are blended without discipline. The averages look healthy. The question they're answering has quietly changed.

The fix was not more SQL. The fix was respecting the domain properly. Competition-aware reporting requires separate marts, separate grains, and explicit competition-type filtering at model definition time — not a `WHERE` clause at query time that depends on every consumer remembering to apply it.

The domain itself shaped the architecture. That is how domain modelling is supposed to work.

---

## 07 — Data Quality

### The model that didn't ship

Not all engineering decisions involve building something. Some of the more important ones involve stopping.

The original project scope included coach dimensions and historical coaching period models. The ingestion was written, the staging models were drafted, and the intermediate logic was taking shape. Then the API returned something that made further progress impossible to defend.

---

### Incident: The same coach managing France and Spain simultaneously

A single coach record was returned as the active manager of two different national teams at the same time. Not adjacent time periods. Not a transfer in progress. Simultaneously.

The issue was upstream — an API data quality problem, not a modelling error. But that distinction does not matter to the analyst consuming the output. A coach dimension built on that data would have been wrong in production from day one, silently, without any obvious indicator.

**Decision made:** keep the ingestion, remove all downstream coach models entirely. No staging exposure, no intermediate logic, no mart outputs. Missing feature, not broken feature.

> Bad data entering production quietly is worse than a missing capability. A missing dimension tells the consumer nothing exists. A wrong dimension tells them something false. These are not equivalent outcomes.

---

This decision is harder to defend than shipping would have been. Shipping produces visible output. Not shipping requires explaining an absence. But engineering maturity is partly the ability to make that case — to distinguish between "we haven't built this yet" and "we built this and it's not safe to use."

Every subsequent dimension now has an explicit data quality check before the downstream models are considered stable. The coach incident made the cost of skipping that step concrete rather than theoretical.

---

## 08 — Observability

### A platform running unmonitored is a platform running on trust

The fetch_transfers incident made one thing clear: silent failures are the most expensive kind. A job that runs for twenty hours and completes successfully is fine. A job that runs for twenty hours, produces subtly wrong output, and gets consumed by downstream models is a different problem entirely — one that surfaces weeks later as a data quality issue with no obvious origin.

The structural response was to build monitoring in, not bolt it on afterwards.

Two scripts handle operational health:

**`job_spike_check.py`** queries `ingestion_metadata` across a 30-day window and detects:

- Runtime spikes — flagged when the latest run exceeds 2× the endpoint's average duration
- Failed runs — any endpoint with failures in the last 30 days
- Zero-row over-fetching — flagged when more than 50% of recent runs inserted 0 rows, which indicates the fetch scope is broader than the data warrants

When issues are detected, a triage report is generated and emailed automatically. When nothing is flagged, the report still runs — confirming the system is healthy, not just quiet.

**`send_triage_report.py`** handles the dbt side, emitting model-level failure summaries through the same email pipeline.

The result is that pipeline regressions surface as emails, not as downstream data quality issues noticed weeks later by an analyst who notices a number looks wrong.

> Observability is not a feature. It is the difference between a system you operate and a system that operates you.

---

## 09 — Consumption

### Three different answers to the same underlying data

The platform exposes data through three consumption paths, each designed to answer a different class of question. The distinction is not cosmetic — it shaped how the mart layer was designed.

| Layer | Primary question | Consumer |
|---|---|---|
| Streamlit | What happened and how did it look? Exploratory, visual, specific | Analytical end user, portfolio demonstration |
| LookML | How do I slice this across dimensions I didn't anticipate at model time? | BI consumer, ad-hoc exploration |
| MetricFlow | What is the canonical definition of this metric, regardless of how it's queried? | Any consumer — the semantic layer enforces consistency |

The MetricFlow semantic layer is the least obvious choice to justify, but the most important for long-term consistency. Without it, "club win rate" is whatever SQL the current analyst writes. With it, club win rate has one definition, one grain, one set of competition-type filters — and every consumer gets the same number. The semantic layer is not a BI tool. It is a contract.

This contract becomes the foundation for self-serve analytics. When metrics are defined once and trusted everywhere, analysts don't need to ask an engineer every time they want to slice a number a different way. They query confidently because the definition is stable underneath them.

It also positions the platform for conversational analytics. As AI-powered query interfaces mature — tools that let a business user ask "which clubs improved most in points-per-game between 2023 and 2024?" in plain language — the semantic layer is what makes those answers trustworthy. Without consistent metric definitions, a conversational interface returns confident-sounding numbers that mean different things depending on how the question was phrased. With MetricFlow, the answer is grounded in the same definition every analyst uses.

The three consumption paths — Streamlit, LookML, and MetricFlow — are not alternatives. They complement each other. Streamlit for exploration and visual storytelling. LookML for flexible BI slicing. MetricFlow for consistent, trustworthy metrics that power both — and eventually, conversational interfaces too.

### What the mart layer actually covers

The 18 reporting marts are organised into five domains, each answering a distinct class of business question:

**Domestic league** — club season summaries, live standings, matchweek results, match-by-match form, player season stats per competition, and top scorer charts across the big five leagues.

**Cups and Europe** — how far a club progressed in domestic cups, full UEFA campaign tracking by round with official labels, and a trophy cabinet model that correctly handles trebles and doubles.

**International tournaments** — World Cup and Euros coverage by round and placement, separate from club competition data so national team performance is never blended with club statistics.

**Transfers and valuation** — permanent fee move history, valuation changes between moves, squad fee footprint by season, and `fact_player_club_period` for point-in-time club membership queries.

**Ops and monitoring** — `mart_pipeline_health` and `mart_api_usage` expose ingestion run outcomes and API quota consumption directly in Streamlit, so operational visibility is a first-class product concern, not a separate tool.

League stats and cup stats live in separate marts. Blending them produces metrics that look correct and mean something different. The domain knowledge section explains why in detail.

---

## 10 — What's Next

### The open problems

The platform is functional. These are the decisions that remain genuinely unresolved — not missing features, but architectural questions where the right answer is not yet clear.

| Open question | Why it's unresolved |
|---|---|
| Bronze-layer replayability | Adds correct separation, but requires re-architecting ingestion. The cost is real and the benefit is long-term — difficult tradeoff to time correctly |
| Dedicated orchestration | Databricks Jobs works, but a migration to Airflow or Dagster would give finer-grained dependency control and better failure isolation across the ingestion-to-transformation boundary |
| External market valuations | Transfermarkt-style valuation data would make squad valuation marts significantly more useful, but introduces a second API relationship and schema divergence risk |
| Stale mart detection | Observability currently covers ingestion health. Detecting which marts are stale relative to their upstream ingestion runs — and alerting on that specifically — is not yet automated |

---

## Final Reflection

This project started as a football platform.

It became a systems-thinking project about architecture, modelling, tradeoffs, scale, and curiosity.

The technical artefacts matter — ingestion pipelines, marts, snapshots, semantic models, dashboards, orchestration, observability scripts, and ADRs. But the deeper lesson was learning how to sit with complexity long enough to understand it properly.

Football turned out not to be the easy part. That was exactly why the project became worth building.

---
