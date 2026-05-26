# dbt Triage

Triage the last dbt run. Detect failures, investigate the root cause, and summarise what broke and how bad it is.

## Steps

### 1. Detect failures
Read `target/run_results.json`. Parse every result node and separate into:
- **Model errors** — status = `error`
- **Test failures** — status = `fail`
- **Warnings** — status = `warn`
- **Skipped** — status = `skipped`

If there are no failures, report "All nodes passed" and stop.

### 2. For each failed model (status = error)
- Read the model SQL file from `models/`
- Report the error message from `run_results.json`
- Identify which CTE or join is most likely responsible based on the error message
- Check if the failure is a compilation error (Jinja/SQL syntax) or a runtime error (data issue)

**Known error patterns and fixes:**
- `DELTA_MERGE_UNRESOLVED_EXPRESSION` — schema mismatch between the existing Delta table and the
  current model output. Caused by renamed or added columns since the table was last built.
  Fix: `dbt run --select <model_name> --full-refresh` to drop and recreate the table cleanly.
- `Table or view not found` — model references a source or ref that hasn't been materialised yet.
  Fix: run the upstream model first, or use `dbt run --select +<model_name>` to include dependencies.

### 3. For each failed test (status = fail)
- Report which model and column the test is on
- Report the number of failing rows from `failures` field
- Run the compiled test SQL against Databricks to show a sample of failing rows (LIMIT 10)
- Determine severity: if failures > 1% of total rows it is HIGH, otherwise LOW

### 4. Investigate root cause
For HIGH severity failures or model errors:
- Query the relevant raw or staging table in Databricks to check if source data is the issue
- Check `football_raw.ingestion_metadata` for recent failed ingestion runs on the relevant endpoint
- Read the model's schema.yml entry to check if the test expectation is reasonable

### 5. Summarise
Present a triage report with:
- Total nodes run, passed, failed, warned
- For each failure: model/test name, severity (HIGH/LOW), likely root cause, recommended action
- Whether the failure is a data issue (source problem) or a code issue (model/test problem)

Keep the report concise — one line per failure for LOW severity, a short paragraph for HIGH severity.

### 6. Send email report
If there are any failures, pipe the triage report to the email script:

```bash
echo "<triage report text>" | python scripts/send_triage_report.py "dbt Triage — <N> failure(s) detected"
```

Requires the following environment variables to be set:
- `GMAIL_USER` — your Gmail address
- `GMAIL_APP_PASSWORD` — Gmail app password (generate at myaccount.google.com/apppasswords)
- `TRIAGE_RECIPIENT_EMAIL` — recipient address (defaults to GMAIL_USER if not set)

### 7. Create GitHub issue for HIGH severity failures
For each HIGH severity failure, create a GitHub issue:

```bash
gh issue create \
  --title "dbt failure: <model_or_test_name>" \
  --body "<root cause summary, failing rows sample, recommended action>" \
  --label "data-quality" \
  --assignee "@me"
```

Skip this step for LOW severity failures — those are informational only.
