#!/usr/bin/env bash
# Apply the serialized football-analytics Databricks job definition.
#
# Prerequisites:
#   - Databricks CLI v0.200+ configured (`databricks auth login`)
#   - JOB_ID set if updating an existing job, or leave unset to create a new one
#
# Usage:
#   export JOB_ID=123456789012345   # optional — omit to create
#   ./scripts/ingestion/deploy_databricks_job.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
JOB_JSON="$ROOT/scripts/ingestion/databricks_job.json"

if ! command -v databricks >/dev/null 2>&1; then
  echo "Databricks CLI not found. Install: https://docs.databricks.com/dev-tools/cli/"
  exit 1
fi

if [[ -n "${JOB_ID:-}" ]]; then
  echo "Updating job $JOB_ID from $JOB_JSON ..."
  databricks jobs reset --json @"$JOB_JSON" --job-id "$JOB_ID"
  echo "Done. Job URL: $(databricks jobs get --job-id "$JOB_ID" --output json | python3 -c 'import json,sys; print(json.load(sys.stdin).get("settings",{}).get("url",""))' 2>/dev/null || echo "(see Databricks UI)")"
else
  echo "Creating new job from $JOB_JSON ..."
  JOB_ID="$(databricks jobs create --json @"$JOB_JSON" --output json | python3 -c 'import json,sys; print(json.load(sys.stdin)["job_id"])')"
  echo "Created job_id=$JOB_ID"
  echo "Save this ID: export JOB_ID=$JOB_ID"
fi
