# Scripts

## Scheduled ops (laptop cron)

Runs from your Mac via `crontab` — not GitHub Actions.

| Script | Purpose |
|--------|---------|
| `job_spike_check.py` | Ingestion runtime / failure / zero-row spikes → email |
| `dbt_alert.py` | Parse `target/run_results.json` → triage report → `send_triage_report` |
| `send_triage_report.py` | Email helper (stdin or imported by `dbt_alert`) |
| `run_scheduled_ops.sh` | Cron entrypoint: runs both checks |

### Setup (one time)

```bash
cd /Users/efuatutuwaa-ampofo/Desktop/dbt/football-analytics-dbt
cp .env.example .env          # DATABRICKS_* + GMAIL_*
chmod +x scripts/run_scheduled_ops.sh
./scripts/run_scheduled_ops.sh   # test manually
crontab -e                       # paste line from scripts/crontab.example
```

### Schedule

Default in `crontab.example`: **09:00 local time** daily (after a typical overnight Databricks run).

Your laptop must be **on and awake** at that time for cron to fire.

### dbt triage note

`dbt_alert` only runs if `target/run_results.json` exists locally (e.g. after you run `dbt test` on your machine). Spike check always runs against Databricks.

### Logs

`logs/scheduled_ops_YYYYMMDD_HHMMSS.log`
