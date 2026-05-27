#!/usr/bin/env bash
# Scheduled ops: ingestion spike check + dbt triage email.
# Intended for cron or manual runs after the Databricks pipeline completes.
#
# Usage:
#   ./scripts/run_scheduled_ops.sh
#
# Requires .env in the project root (see .env.example).

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

LOG_DIR="${ROOT}/logs"
mkdir -p "$LOG_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_DIR}/scheduled_ops_${STAMP}.log"

exec > >(tee -a "$LOG_FILE") 2>&1

echo "=== scheduled ops $(date -u '+%Y-%m-%d %H:%M UTC') ==="

if [[ -f "${ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${ROOT}/.env"
  set +a
else
  echo "WARNING: ${ROOT}/.env not found — set env vars or copy from .env.example"
fi

PYTHON="python3"
if [[ -x "${ROOT}/../dbt-env/bin/python" ]]; then
  PYTHON="${ROOT}/../dbt-env/bin/python"
elif [[ -x "${ROOT}/.venv/bin/python" ]]; then
  PYTHON="${ROOT}/.venv/bin/python"
fi

echo "--- job_spike_check ---"
"$PYTHON" scripts/job_spike_check.py

echo "--- dbt triage (dbt_alert → send_triage_report) ---"
if [[ -f "${ROOT}/target/run_results.json" ]]; then
  "$PYTHON" scripts/dbt_alert.py
else
  echo "Skipping dbt triage — target/run_results.json not found."
  echo "Run after a local dbt run, or add a Databricks Job task after dbt test."
fi

echo "=== done — log: ${LOG_FILE} ==="
