# dbt Semantic Layer (MetricFlow)

YAML lives under **`models/semantic/`** (inside `model-paths`). dbt 1.11 does **not** support `semantic-models-paths` in `dbt_project.yml`.

## Time spine (required)

If semantic models or metrics YAML exist anywhere under `models/`, dbt **1.11** validates MetricFlow on every command (`dbt run`, `dbt snapshot`, etc.) and requires a **daily time spine**:

| Resource | File |
|----------|------|
| Table | `time_spine_daily.sql` → schema `football_semantic` |
| Config | `_time_spine.yml` (`time_spine.standard_granularity_column: date_day`) |

Build once:

```bash
dbt run --select time_spine_daily
```

[MetricFlow time spine docs](https://docs.getdbt.com/docs/build/metricflow-time-spine)

## Demo semantic models

| Semantic model | dbt model | Time dimension | Use |
|----------------|-----------|----------------|-----|
| `club_season` | `mart_club_season` | `league_season` (year) | League table style metrics |
| `player_season` | `mart_player_season` | `league_season` (year) | Top scorers, minutes, shots, per-90, rating |
| `transfer_window` | `mart_transfer_window` | `transfer_date` (day) | Fee move counts by window |
| `player_value_changes` | `mart_player_value_changes` | `transfer_date` (day) | EUR fees and fee deltas |
| `national_team_honours` | `mart_national_team_honours` | `league_season` (year) | WC/Euros podium and wins |
| `club_honours` | `mart_club_honours` | `league_season` (year) | Trophy cabinet / treble counts |
| `club_european_performance` | `mart_club_european_performance` | `league_season` (year) | UCL / CWC campaigns, farthest round, winners |

Season years (`2024`) use `make_date(league_season, 1, 1)` at **year** grain. Transfer marts use **`transfer_date`** at **day** grain.

**MetricFlow rule:** each `(primary entity, dimension)` name pair must be **unique across all semantic models** in the project — so honours/transfer/European models use prefixed names (`honoured_club`, `european_club`, etc.) even when the SQL column is the same.

Metrics: `metrics.yml` (~21 metrics; includes European club goals and tournament wins).

Query with `dbt sl` requires the MetricFlow CLI (dbt 1.11+ / Fusion). If you see `No such command 'sl'`, use `dbt parse` to validate YAML, or install/enable the semantic-layer extra for your dbt install.

## Prerequisites

- Marts built: `dbt run --select path:models/marts`
- Time spine built (above)

## Commands

```bash
dbt parse
dbt sl list metrics
```

## Scope

Demo slice only — not all 18 marts (7 covered). Snapshots do **not** use MetricFlow; they only need a valid project parse. See `../../looker/` and `../../app/`.
