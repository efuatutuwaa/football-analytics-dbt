"""Ingestion pipeline health — mart_pipeline_health (+ mart_api_usage)."""

import altair as alt
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib.db import ops_table, run_query

LOOKBACK_OPTIONS = [7, 14, 30, 60, 90]
TOP_ENDPOINTS = 10
STATUS_COLORS = {
    "success": "#2e7d32",
    "skipped": "#e8f5e9",
    "failed": "#c62828",
}
HEATMAP_COLORSCALE = [
    [0.0, "#ffffff"],
    [0.001, "#c8e6c9"],
    [0.3, "#66bb6a"],
    [0.7, "#2e7d32"],
    [1.0, "#0a3d1f"],
]
DAILY_QUOTA = 75_000

st.header("Ops pipeline")
st.caption(
    "Ingestion pipeline health and API quota usage · powered by "
    "mart_pipeline_health and mart_api_usage."
)

filter_col1, filter_col2 = st.columns(2)
with filter_col1:
    days = st.selectbox(
        "Look back (days)",
        LOOKBACK_OPTIONS,
        index=LOOKBACK_OPTIONS.index(30),
        key="ops_pipeline_days",
    )
with filter_col2:
    endpoint_filter = st.text_input("Endpoint contains (optional)", value="")

endpoint_clause = ""
if endpoint_filter.strip():
    safe = endpoint_filter.strip().replace("'", "''")
    endpoint_clause = f"and lower(endpoint) like lower('%{safe}%')"

status_sql = f"""
select
    status,
    count(*) as runs
from {ops_table("mart_pipeline_health")}
where run_date >= date_sub(current_date(), {days})
{endpoint_clause}
group by status
order by runs desc
"""

failed_sql = f"""
select
    run_date,
    endpoint,
    entity_id,
    status,
    rows_inserted,
    requests_used
from {ops_table("mart_pipeline_health")}
where status = 'failed'
  and run_date >= date_sub(current_date(), {days})
{endpoint_clause}
order by run_date desc, endpoint
limit 50
"""

runs_sql = f"""
select
    run_date,
    endpoint,
    entity_id,
    status,
    rows_inserted,
    requests_used,
    runtime_minutes,
    run_started_at
from {ops_table("mart_pipeline_health")}
where run_date >= date_sub(current_date(), {days})
{endpoint_clause}
order by run_started_at desc
limit 200
"""

usage_by_day_sql = f"""
select
    run_date,
    sum(total_requests) as total_requests,
    sum(total_rows_inserted) as total_rows_inserted,
    sum(successful_runs) as successful_runs,
    sum(failed_runs) as failed_runs
from {ops_table("mart_api_usage")}
where run_date >= date_sub(current_date(), {days})
{endpoint_clause}
group by run_date
order by run_date
"""

usage_by_endpoint_sql = f"""
select
    endpoint,
    sum(total_requests) as total_requests,
    sum(failed_runs) as failed_runs
from {ops_table("mart_api_usage")}
where run_date >= date_sub(current_date(), {days})
{endpoint_clause}
group by endpoint
order by total_requests desc
limit {TOP_ENDPOINTS}
"""


def avg_success_runtime(runs_df: pd.DataFrame) -> str:
    if runs_df.empty:
        return "—"
    success_runtimes = runs_df.loc[
        (runs_df["status"] == "success") & runs_df["runtime_minutes"].notna(),
        "runtime_minutes",
    ]
    if success_runtimes.empty:
        return "—"
    return f"{round(float(success_runtimes.mean()), 2)}"


def status_donut(status_df: pd.DataFrame) -> None:
    labels = status_df["status"].tolist()
    values = [int(v) for v in status_df["runs"].tolist()]
    colors = [STATUS_COLORS.get(str(label), "#94a3b8") for label in labels]

    failed_total = sum(v for label, v in zip(labels, values) if str(label) == "failed")
    center_subtitle = "pipeline healthy" if failed_total == 0 else "needs attention"

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.55,
                marker=dict(colors=colors, line=dict(color="rgba(0,0,0,0)", width=0)),
                textinfo="label+percent",
                hovertemplate="<b>%{label}</b><br>%{value} runs<br>%{percent}<extra></extra>",
                sort=False,
            )
        ]
    )
    fig.update_layout(
        showlegend=False,
        annotations=[
            dict(
                text=(
                    f"<b style='font-size:28px'>{failed_total:,} "
                    f"{'failure' if failed_total == 1 else 'failures'}</b>"
                    f"<br><span style='font-size:13px'>{center_subtitle}</span>"
                ),
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=22),
            )
        ],
        margin=dict(l=20, r=20, t=20, b=20),
        height=350,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)


def daily_requests_heatmap(usage_df: pd.DataFrame) -> None:
    plot_df = usage_df.copy()
    plot_df["run_date"] = pd.to_datetime(plot_df["run_date"])
    plot_df["total_requests"] = pd.to_numeric(plot_df["total_requests"], errors="coerce").fillna(0)
    daily_df = (
        plot_df.groupby("run_date", as_index=False)["total_requests"]
        .sum()
        .sort_values("run_date")
        .reset_index(drop=True)
    )

    if daily_df.empty:
        return

    daily_df["date_str"] = daily_df["run_date"].dt.strftime("%-d %b")
    daily_df["requests"] = daily_df["total_requests"].astype(int)

    z = [daily_df["requests"].tolist()]
    x = daily_df["date_str"].tolist()
    y = [""]

    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=x,
            y=y,
            colorscale=HEATMAP_COLORSCALE,
            showscale=True,
            xgap=2,
            ygap=2,
            hovertemplate="%{x}<br>Requests: %{z:,}<extra></extra>",
        )
    )

    fig.update_layout(
        height=140,
        margin=dict(l=10, r=80, t=10, b=80),
        xaxis=dict(
            type="category",
            tickangle=-45,
            tickfont=dict(size=11),
            fixedrange=True,
        ),
        yaxis=dict(
            showticklabels=False,
            fixedrange=True,
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )

    st.plotly_chart(fig, use_container_width=True)

    max_requests = int(daily_df["requests"].max())
    if max_requests >= DAILY_QUOTA * 0.8:
        st.warning(
            f"Daily API quota: {DAILY_QUOTA:,} requests · peak in window: "
            f"{max_requests:,}."
        )
    else:
        st.caption(f"Daily API quota: {DAILY_QUOTA:,} requests.")


def endpoint_bar_chart(endpoint_df: pd.DataFrame) -> None:
    plot_df = endpoint_df.copy()
    request_rank = pd.to_numeric(plot_df["total_requests"], errors="coerce").fillna(0).astype("float64")
    plot_df = plot_df.iloc[request_rank.argsort()[::-1]].reset_index(drop=True)
    plot_df = plot_df.head(TOP_ENDPOINTS)
    plot_df = plot_df.iloc[::-1].reset_index(drop=True)

    chart = (
        alt.Chart(plot_df)
        .mark_bar(color="#4a90d9")
        .encode(
            x=alt.X("total_requests:Q", title="Requests"),
            y=alt.Y(
                "endpoint:N",
                sort="-x",
                title="",
                axis=alt.Axis(labelLimit=0),
            ),
            tooltip=[
                alt.Tooltip("endpoint:N", title="Endpoint"),
                alt.Tooltip("total_requests:Q", title="Requests", format=","),
                alt.Tooltip("failed_runs:Q", title="Failed runs"),
            ],
        )
        .properties(
            height=max(320, len(plot_df) * 28),
            padding={"left": 200, "top": 10, "right": 10, "bottom": 10},
        )
        .configure_view(strokeWidth=0)
    )
    st.altair_chart(chart, use_container_width=True)


try:
    status = run_query(status_sql)
    failed = run_query(failed_sql)
    runs = run_query(runs_sql)
    usage_day = run_query(usage_by_day_sql)
    usage_endpoint = run_query(usage_by_endpoint_sql)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Runs (sample)", len(runs))
    c2.metric("Failed runs", len(failed))
    c3.metric(
        "API requests",
        int(usage_day["total_requests"].sum()) if len(usage_day) else 0,
    )
    c4.metric("Avg runtime (min)", avg_success_runtime(runs))

    if not status.empty:
        st.subheader("Runs by status")
        status_donut(status)

    if not usage_day.empty:
        st.subheader("Daily API requests")
        daily_requests_heatmap(usage_day)

    if not usage_endpoint.empty:
        st.subheader(f"Requests by endpoint — top {TOP_ENDPOINTS}")
        endpoint_bar_chart(usage_endpoint)

    if not failed.empty:
        st.subheader("Recent failures")
        st.dataframe(failed, use_container_width=True, hide_index=True)
except KeyError:
    st.error("Set DATABRICKS_HOST, DATABRICKS_HTTP_PATH, and DATABRICKS_TOKEN (see app/.env.example).")
except Exception as exc:  # noqa: BLE001
    st.exception(exc)
