"""
dbt_alert.py — automated triage after a dbt run.

Parses target/run_results.json, generates a triage report, sends it via Gmail,
and opens a GitHub issue for HIGH severity failures.

Usage:
    python scripts/dbt_alert.py

Environment variables required:
    GMAIL_USER              — Gmail address to send from
    GMAIL_APP_PASSWORD      — Gmail app password (myaccount.google.com/apppasswords)
    TRIAGE_RECIPIENT_EMAIL  — recipient address (defaults to GMAIL_USER)
    GITHUB_REPO             — owner/repo for GitHub issues (e.g. efua/football-analytics-dbt)
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from send_triage_report import send_report  # noqa: E402

load_dotenv()

RUN_RESULTS_PATH = Path("target/run_results.json")
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
RECIPIENT_EMAIL = os.environ.get("TRIAGE_RECIPIENT_EMAIL", GMAIL_USER)
GITHUB_REPO = os.environ.get("GITHUB_REPO")

HIGH_SEVERITY_FAILURE_THRESHOLD = 0.01  # 1% of rows

ERROR_PATTERNS = {
    "DELTA_MERGE_UNRESOLVED_EXPRESSION": (
        "Schema mismatch between existing Delta table and current model output. "
        "Fix: dbt run --select <model> --full-refresh"
    ),
    "Table or view not found": (
        "Upstream model or source has not been materialised yet. "
        "Fix: dbt run --select +<model> to include dependencies."
    ),
}


def load_run_results() -> dict:
    if not RUN_RESULTS_PATH.exists():
        print("No run_results.json found — has dbt run been executed?")
        sys.exit(0)
    with open(RUN_RESULTS_PATH) as f:
        return json.load(f)


def parse_results(data: dict) -> dict:
    summary = {"errors": [], "failures": [], "warnings": [], "passed": 0, "skipped": 0}

    for result in data.get("results", []):
        status = result["status"]
        node_id = result["unique_id"]
        failures = result.get("failures") or 0
        message = result.get("message") or ""

        if status == "error":
            summary["errors"].append({"id": node_id, "message": message})
        elif status == "fail":
            summary["failures"].append(
                {"id": node_id, "failures": failures, "message": message}
            )
        elif status == "warn":
            summary["warnings"].append({"id": node_id, "message": message})
        elif status == "success":
            summary["passed"] += 1
        elif status == "skipped":
            summary["skipped"] += 1

    return summary


def classify_severity(failure: dict, total_rows: int) -> str:
    if failure.get("failures", 0) > total_rows * HIGH_SEVERITY_FAILURE_THRESHOLD:
        return "HIGH"
    return "LOW"


def build_report(summary: dict) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total = (
        summary["passed"]
        + len(summary["errors"])
        + len(summary["failures"])
        + len(summary["warnings"])
        + summary["skipped"]
    )

    lines = [
        f"dbt Triage Report — {now}",
        "=" * 60,
        f"Total nodes : {total}",
        f"Passed      : {summary['passed']}",
        f"Errors      : {len(summary['errors'])}",
        f"Test fails  : {len(summary['failures'])}",
        f"Warnings    : {len(summary['warnings'])}",
        f"Skipped     : {summary['skipped']}",
        "",
    ]

    if summary["errors"]:
        lines.append("MODEL ERRORS")
        lines.append("-" * 40)
        for e in summary["errors"]:
            name = e["id"].split(".")[-1]
            lines.append(f"  [ERROR] {name}")
            if e["message"]:
                lines.append(f"          {e['message']}")
            for pattern, fix in ERROR_PATTERNS.items():
                if pattern in (e["message"] or ""):
                    lines.append(f"          FIX: {fix}")
                    break
        lines.append("")

    if summary["failures"]:
        lines.append("TEST FAILURES")
        lines.append("-" * 40)
        for f in summary["failures"]:
            name = f["id"].split(".")[-1]
            severity = "HIGH" if f["failures"] and f["failures"] > 100 else "LOW"
            lines.append(f"  [{severity}] {name} — {f['failures']} failing rows")
        lines.append("")

    if summary["warnings"]:
        lines.append("WARNINGS")
        lines.append("-" * 40)
        for w in summary["warnings"]:
            name = w["id"].split(".")[-1]
            lines.append(f"  [WARN] {name}: {w['message']}")
        lines.append("")

    if not summary["errors"] and not summary["failures"]:
        lines.append("All nodes passed. No action required.")

    return "\n".join(lines)


def create_github_issue(name: str, body: str) -> None:
    if not GITHUB_REPO:
        print("GitHub issue skipped — GITHUB_REPO not set.")
        return

    result = subprocess.run(
        [
            "gh",
            "issue",
            "create",
            "--repo",
            GITHUB_REPO,
            "--title",
            f"dbt failure: {name}",
            "--body",
            body,
            "--label",
            "data-quality",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print(f"GitHub issue created: {result.stdout.strip()}")
    else:
        print(f"GitHub issue creation failed: {result.stderr.strip()}")


def main() -> None:
    data = load_run_results()
    summary = parse_results(data)
    report = build_report(summary)

    print(report)

    has_failures = summary["errors"] or summary["failures"]
    error_count = len(summary["errors"]) + len(summary["failures"])

    if has_failures:
        subject = f"dbt alert — {error_count} failure(s) detected"
    else:
        subject = "dbt run — all nodes passed"

    if GMAIL_USER and GMAIL_APP_PASSWORD:
        send_report(subject, report)
    else:
        print("Email skipped — GMAIL_USER or GMAIL_APP_PASSWORD not set.")

    # open github issues for model errors and HIGH severity test failures
    for error in summary["errors"]:
        name = error["id"].split(".")[-1]
        create_github_issue(
            name, f"**Model error**\n\n```\n{error['message']}\n```\n\n{report}"
        )

    for failure in summary["failures"]:
        if failure.get("failures", 0) > 100:
            name = failure["id"].split(".")[-1]
            create_github_issue(
                name,
                f"**Test failure — {failure['failures']} failing rows**\n\n{report}",
            )


if __name__ == "__main__":
    main()
