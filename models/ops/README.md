# Ops layer (`football_ops`)

Monitoring marts over `football_raw.ingestion_metadata` — not for football analytics BI.

| Model | Grain | Use |
|-------|-------|-----|
| `mart_pipeline_health` | 1 row / run (`endpoint`, `entity_id`, `run_started_at`) | Failures, runtime spikes, per-entity status |
| `mart_api_usage` | 1 row / day / endpoint | API quota and daily request volume |

## Run

```bash
dbt run --select path:models/ops
dbt test --select path:models/ops
```

Requires `ingestion_metadata` populated by Python fetch scripts under `scripts/ingestion/`.
