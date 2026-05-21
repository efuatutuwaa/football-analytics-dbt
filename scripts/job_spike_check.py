"""
job_spike_check.py — automated ingestion job spike detection.

Queries ingestion_metadata to detect runtime spikes, data gaps, failed runs,
and zero-row over-fetching. Sends a report via Gmail.

Usage:
    python scripts/job_spike_check.py

Environment variables required:
    DATABRICKS_HOST         — Databricks workspace host
    DATABRICKS_HTTP_PATH    — SQL warehouse HTTP path
    DATABRICKS_TOKEN        — Databricks personal access token
    GMAIL_USER              — Gmail address to send from
    GMAIL_APP_PASSWORD      — Gmail app password
    TRIAGE_RECIPIENT_EMAIL  — recipient address (defaults to GMAIL_USER)
"""

import os
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from databricks import sql
from dotenv import load_dotenv

load_dotenv()

DATABRICKS_HOST = os.environ["DATABRICKS_HOST"]
DATABRICKS_HTTP_PATH = os.environ["DATABRICKS_HTTP_PATH"]
DATABRICKS_TOKEN = os.environ["DATABRICKS_TOKEN"]
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
RECIPIENT_EMAIL = os.environ.get("TRIAGE_RECIPIENT_EMAIL", GMAIL_USER)

SPIKE_MULTIPLIER = 2.0  # flag if latest run > 2x average duration
ZERO_ROW_THRESHOLD = 0.5  # flag if >50% of runs in last 7 days inserted 0 rows


def run_query(cursor, sql_query: str) -> list:
    cursor.execute(sql_query)
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_endpoint_stats(cursor) -> list:
    return run_query(
        cursor,
        """
        SELECT
            endpoint,
            count(*)                                                            as total_runs,
            avg(timestampdiff(SECOND, started_at, last_ingested_at))            as avg_duration_seconds,
            max(timestampdiff(SECOND, started_at, last_ingested_at))            as max_duration_seconds,
            avg(rows_inserted)                                                  as avg_rows_inserted,
            max(rows_inserted)                                                  as max_rows_inserted,
            sum(case when status = 'failed' then 1 else 0 end)                 as failed_runs,
            sum(case when rows_inserted = 0 then 1 else 0 end)                 as zero_row_runs,
            sum(requests_used)                                                  as total_requests
        FROM efua_data_platform.football_raw.ingestion_metadata
        WHERE started_at >= current_date - 30
        GROUP BY endpoint
        ORDER BY avg_duration_seconds desc
    """,
    )


def get_latest_run(cursor, endpoint: str) -> dict:
    rows = run_query(
        cursor,
        f"""
        SELECT
            timestampdiff(SECOND, started_at, last_ingested_at) as duration_seconds,
            rows_inserted,
            status,
            last_ingested_at
        FROM efua_data_platform.football_raw.ingestion_metadata
        WHERE endpoint = '{endpoint}'
        ORDER BY started_at DESC
        LIMIT 1
    """,
    )
    return rows[0] if rows else {}


def detect_spikes(stats: list, cursor) -> list:
    flagged = []
    for row in stats:
        endpoint = row["endpoint"]
        avg_dur = row["avg_duration_seconds"] or 0
        failed = row["failed_runs"] or 0
        zero_rows = row["zero_row_runs"] or 0
        total = row["total_runs"] or 1
        latest = get_latest_run(cursor, endpoint)
        latest_dur = latest.get("duration_seconds") or 0
        issues = []

        if avg_dur > 0 and latest_dur > avg_dur * SPIKE_MULTIPLIER:
            issues.append(
                f"runtime spike: {latest_dur:.0f}s vs {avg_dur:.0f}s avg ({latest_dur/avg_dur:.1f}x)"
            )

        if failed > 0:
            issues.append(f"{int(failed)} failed run(s) in last 30 days")

        if zero_rows / total > ZERO_ROW_THRESHOLD:
            issues.append(
                f"{zero_rows/total*100:.0f}% of runs inserted 0 rows (possible over-fetching)"
            )

        if issues:
            flagged.append({"endpoint": endpoint, "issues": issues, "latest": latest})

    return flagged


def build_report(stats: list, flagged: list) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total_requests = sum(r.get("total_requests") or 0 for r in stats)

    lines = [
        f"Job Spike Report — {now}",
        "=" * 60,
        f"Endpoints monitored : {len(stats)}",
        f"Endpoints flagged   : {len(flagged)}",
        f"Total API requests  : {int(total_requests)} (last 30 days)",
        "",
    ]

    if flagged:
        lines.append("FLAGGED ENDPOINTS")
        lines.append("-" * 40)
        for f in flagged:
            lines.append(f"  [{f['endpoint']}]")
            for issue in f["issues"]:
                lines.append(f"    - {issue}")
        lines.append("")

    lines.append("ALL ENDPOINTS (last 30 days)")
    lines.append("-" * 40)
    for row in stats:
        status = (
            "FLAG" if any(f["endpoint"] == row["endpoint"] for f in flagged) else "OK"
        )
        lines.append(
            f"  [{status}] {row['endpoint']:<40} "
            f"avg {row['avg_duration_seconds'] or 0:.0f}s  "
            f"runs {int(row['total_runs'])}  "
            f"zero-rows {int(row['zero_row_runs'] or 0)}"
        )

    return "\n".join(lines)


def send_email(subject: str, body: str) -> None:
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        print("Email skipped — GMAIL_USER or GMAIL_APP_PASSWORD not set.")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = RECIPIENT_EMAIL

    html = f"""
    <html><body>
    <h2 style="color:#2980b9;">Job Spike Report</h2>
    <p style="color:#666;">Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</p>
    <hr/>
    <pre style="font-family:monospace;font-size:13px;background:#f4f4f4;padding:16px;border-radius:6px;">
{body}
    </pre>
    <hr/>
    <p style="color:#999;font-size:11px;">football-analytics-dbt · automated spike check</p>
    </body></html>
    """

    msg.attach(MIMEText(body, "plain"))
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, RECIPIENT_EMAIL, msg.as_string())

    print(f"Report emailed to {RECIPIENT_EMAIL}")


def main() -> None:
    with sql.connect(
        server_hostname=DATABRICKS_HOST,
        http_path=DATABRICKS_HTTP_PATH,
        access_token=DATABRICKS_TOKEN,
    ) as conn:
        with conn.cursor() as cursor:
            stats = get_endpoint_stats(cursor)
            flagged = detect_spikes(stats, cursor)

    report = build_report(stats, flagged)
    print(report)

    n = len(flagged)
    subject = (
        f"Job Spike Report — {n} endpoint(s) flagged"
        if n
        else "Job Spike Report — all clear"
    )
    send_email(subject, report)


if __name__ == "__main__":
    main()
