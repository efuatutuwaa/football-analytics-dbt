# Scripts

## Scheduled ops (cron)

| Script | Purpose |
|--------|---------|
| `job_spike_check.py` | Ingestion runtime / failure / zero-row spikes → email |
| `dbt_alert.py` | Parse `target/run_results.json` → triage report → `send_triage_report` |
| `send_triage_report.py` | Email helper (stdin or imported by `dbt_alert`) |
| `run_scheduled_ops.sh` | Runs spike check + dbt triage (cron entrypoint) |

### Local cron (Mac)

1. `cp .env.example .env` and fill credentials
2. `chmod +x scripts/run_scheduled_ops.sh`
3. `crontab -e` — see `scripts/crontab.example`

### GitHub Actions

`.github/workflows/scheduled-ops.yml` runs **job spike check** daily (06:00 UTC).

Add repo secrets: `DBT_DATABRICKS_*`, `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `TRIAGE_RECIPIENT_EMAIL`.

### Databricks (dbt triage after pipeline)

`target/run_results.json` lives on the cluster after `run_dbt.py` tasks. Add a final Job task:

```python
%pip install python-dotenv
# secrets + run from repo root:
# python scripts/dbt_alert.py
```

Or run `dbt_alert.py` locally after `dbt test` when `target/` is present.
