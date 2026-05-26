# Job Spike Check

Analyse ingestion job run times and row counts from ingestion_metadata to detect anomalies,
spikes, and unexpected behaviour across all endpoints.

## Steps

### 1. Pull runtime and volume stats per endpoint
Query ingestion_metadata for the last 30 days:

```sql
SELECT
    endpoint,
    count(*)                                                as total_runs,
    avg(timestampdiff(SECOND, started_at, last_ingested_at)) as avg_duration_seconds,
    max(timestampdiff(SECOND, started_at, last_ingested_at)) as max_duration_seconds,
    min(timestampdiff(SECOND, started_at, last_ingested_at)) as min_duration_seconds,
    avg(rows_inserted)                                      as avg_rows_inserted,
    max(rows_inserted)                                      as max_rows_inserted,
    sum(case when status = 'failed' then 1 else 0 end)      as failed_runs,
    sum(case when rows_inserted = 0 then 1 else 0 end)      as zero_row_runs
FROM efua_data_platform.football_raw.ingestion_metadata
WHERE started_at >= current_date - 30
GROUP BY endpoint
ORDER BY avg_duration_seconds desc
```

### 2. Detect spikes
Flag any endpoint where:
- Latest run duration is more than 2x the 30-day average (runtime spike)
- Latest run inserted 0 rows but previous runs inserted > 0 (data gap)
- Failed runs > 0 in the last 7 days
- Zero row runs > 50% of total runs in the last 7 days (possible API issue or over-fetching)

### 3. Drill into flagged endpoints
For each flagged endpoint, query the last 10 runs to show the trend:

```sql
SELECT
    endpoint,
    entity_id,
    started_at,
    last_ingested_at,
    timestampdiff(SECOND, started_at, last_ingested_at) as duration_seconds,
    rows_inserted,
    status
FROM efua_data_platform.football_raw.ingestion_metadata
WHERE endpoint = '<flagged_endpoint>'
ORDER BY started_at DESC
LIMIT 10
```

### 4. Check API rate limit pressure
Flag if total requests_used in the last 24 hours is approaching the daily API limit.
API-Football free tier limit is 100 requests/day, paid tier is higher — check the
x-ratelimit header context if available in logs.

### 5. Known spike patterns
If a spike is detected, check for these known root causes before digging further:

- **transfers endpoint spike** — caused by Spark write-per-player inside the player loop.
  Each player with transfers triggered a full Spark job (plan + schedule + write overhead).
  Fixed in May 2026 by batching all transfers and writing once at the end.
  If it spikes again, check whether the batch write is still in place or was reverted.

- **re-fetch after threshold elapsed** — transfers and player_statistics re-fetch all active
  players once the 30/90-day threshold elapses. Expected runtime is higher on those runs.
  Not a bug — check `ingestion_metadata` to confirm the last full fetch date before escalating.

### 6. Summarise
Present a spike report with:
- Endpoints with runtime spikes (with % above average)
- Endpoints with data gaps (0 rows when rows expected)
- Endpoints with recent failures
- Endpoints burning API quota with no new data (zero-row over-fetching)
- Overall API request usage for the last 24 hours

Keep it concise — one line per healthy endpoint, a short paragraph for any flagged one.

### 6. Send email report
Pipe the spike report to the email script:

```bash
echo "<spike report text>" | python scripts/send_triage_report.py "Job Spike Report — <N> endpoint(s) flagged"
```

Send the email whether or not there are spikes — a clean report is useful confirmation too.
Subject line: "Job Spike Report — all clear" if nothing flagged, "Job Spike Report — <N> endpoint(s) flagged" if issues found.

Requires GMAIL_USER, GMAIL_APP_PASSWORD, and TRIAGE_RECIPIENT_EMAIL set in .env.
