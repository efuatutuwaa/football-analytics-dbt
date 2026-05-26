# Data Catalog

**Football Analytics Platform** · Databricks · dbt · 15 competitions · 2020–present

What exists, at what grain, and which business question each table answers.

**Related docs:** [Case study](docs/case-study.md) · [Architecture](docs/architecture.md)

---

## At a glance

| | |
|---|---|
| **Warehouse** | Databricks (`efua_data_platform`) |
| **Reporting marts** | 18 tables in `football_marts` |
| **Dimensions** | 5 in `football_core` |
| **Ops** | 2 in `football_ops` |
| **Refresh** | Daily ingest → `dbt run` → `dbt test` → `dbt snapshot` |

### Consumption rule

```
✓  Query in BI / Streamlit:  dim_*   fact_*   mart_*
✗  Do not expose:            int_*   snapshots (audit only)
```

---

## Pipeline & freshness

```
API-Football
     ↓
football_raw          ← Python + PySpark ingestion
     ↓
football_staging      ← stg_*
     ↓
football_intermediate ← int_*  (build only — not for BI)
     ↓
football_core         ← dim_*  fact_*
     ↓
football_marts        ← mart_*
     ↓
Streamlit · Looker · MetricFlow
```

| Layer | Schema | What runs |
|---|---|---|
| Ingest | `football_raw` | Python + PySpark · `ingestion_metadata` |
| Staging | `football_staging` | `dbt run` stg_* |
| Intermediate | `football_intermediate` | `dbt run` int_* |
| Core | `football_core` | `dbt run` dim_* · fact_* |
| Marts | `football_marts` | `dbt run` mart_* |
| Ops | `football_ops` | `mart_pipeline_health` · `mart_api_usage` |
| Audit | `football_core` | `dbt snapshot` → `scd_player_club` · `scd_club_league` |

### Freshness thresholds

| Source | Warn | Error |
|---|---|---|
| Default raw tables | 36h without new `ingested_at` | 48h |
| Fixtures, events, stats | Follow daily ingest | — |
| Transfers | 30 days | 7 days during transfer windows |

Config: `models/sources/sources.yml`

---

## Dimensions

Use dimensions to join for names, logos, photos, and flags. Do not use them for campaign totals — those live in marts.

| Model | Grain | Provides |
|---|---|---|
| `dim_club` | `team_id` | Club name · logo |
| `dim_national_team` | `team_id` | Nation · flag |
| `dim_player` | `player_id` | Player name · photo |
| `dim_league` | `league_id` | Competition label |
| `dim_venue` | `venue_id` | Stadium name and location |

---

## Reporting marts

### Domestic league — 7 marts

| Mart | Grain | Business question |
|---|---|---|
| `mart_club_season` | `team_id` · `league_id` · `league_season` | How did this club finish in the league table? |
| `mart_league_standings` | `league_id` · `league_season` · `team_id` · `group_name` | What does the league table look like right now? |
| `mart_league_week` | `league_id` · `league_season` · `league_round` | What happened in this matchweek? |
| `mart_club_matchday` | `fixture_id` · `team_id` | Match-by-match club results + last-5 form |
| `mart_player_season` | `player_id` · `team_id` · `league_id` · `league_season` | Player season stats — per competition, not blended |
| `mart_player_matchday` | `fixture_id` · `player_id` | Single league appearance + rolling form |
| `mart_domestic_league_top_scorers` | `player_id` · `team_id` · `league_id` · `league_season` | Who leads the big-five league scoring charts? |

### Cups and Europe — 3 marts

> League stats and cup stats stay in separate marts. Blending them produces metrics that look correct and mean something different.

| Mart | Grain | Business question |
|---|---|---|
| `mart_club_domestic_cup_performance` | `team_id` · `league_id` · `league_season` | How far did they get in the FA Cup or domestic cup? |
| `mart_club_european_performance` | `team_id` · `league_id` · `league_season` | UCL campaign — farthest round reached (UEFA round labels) |
| `mart_club_honours` | `team_id` · `league_season` | Trophy cabinet — correctly handles trebles and doubles |

### International tournaments — 4 marts

| Mart | Grain | Business question |
|---|---|---|
| `mart_national_team_results` | `team_id` · `league_id` · `league_season` | Full World Cup or Euros run — placement, W/D/L |
| `mart_national_team_honours` | `team_id` · `league_id` · `league_season` | Podium finishes only |
| `mart_world_cup` | `team_id` · `league_season` · `league_round` | World Cup (`league_id = 1`) broken down by round |
| `mart_continental_cups` | `team_id` · `league_id` · `league_season` · `league_round` | Euros (`league_id = 4`) broken down by round |

### Transfers and valuation — 4 marts

| Mart | Grain | Business question |
|---|---|---|
| `mart_transfer_window` | `player_id` · `team_id` · `transfer_date` | Permanent fee moves — when, where, and for how much |
| `mart_player_value_changes` | `player_id` · `team_id` · `transfer_date` | Fee vs previous move (EUR) |
| `mart_player_valuation` | `player_id` · `team_id` · `league_id` · `league_season` | Valuation proxy for a stint |
| `mart_club_squad_value` | `team_id` · `league_id` · `league_season` | Estimated squad fee footprint by season |

**Also in core:** `fact_player_club_period` — which club was a player at on a specific date?

### Ops and monitoring — 2 marts

| Mart | Schema | Grain | Business question |
|---|---|---|---|
| `mart_pipeline_health` | `football_ops` | `endpoint` · `entity_id` · `run_started_at` | Did last night's ingest succeed? How long did it take? |
| `mart_api_usage` | `football_ops` | Daily | Are we approaching API quota limits? |

---

## Streamlit application

| Page | Tables used |
|---|---|
| Club season | `mart_club_season` · `dim_club` |
| Player season | `mart_player_season` · `dim_player` |
| European campaign | `mart_club_european_performance` · `dim_club` |
| Transfers | `mart_player_value_changes` |
| Club honours | `mart_club_honours` · `dim_club` |
| National honours | `mart_national_team_honours` · `dim_national_team` |
| Squad valuation | `mart_club_squad_value` · `dim_club` |
| Pipeline ops | `mart_pipeline_health` · `mart_api_usage` |

---

## Competitions

**Seasons covered:** 2020 → current year

### International

| ID | Competition |
|---|---|
| 1 | FIFA World Cup |
| 4 | UEFA European Championship |
| 2 | UEFA Champions League |
| 15 | FIFA Club World Cup |

### Domestic leagues

| ID | Competition |
|---|---|
| 39 | Premier League |
| 140 | La Liga |
| 135 | Serie A |
| 78 | Bundesliga |
| 61 | Ligue 1 |

### Domestic cups

| ID | Competition |
|---|---|
| 45 | FA Cup |
| 48 | Carabao Cup |
| 143 | Copa del Rey |
| 137 | Coppa Italia |
| 81 | DFB-Pokal |
| 66 | Coupe de France |

---

*football-analytics-dbt · [github.com/efuatutuwaa/football-analytics-dbt](https://github.com/efuatutuwaa/football-analytics-dbt)*