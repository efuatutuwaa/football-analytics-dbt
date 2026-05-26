"""Fee-bearing transfers — mart_player_value_changes (EUR) by destination league."""

import altair as alt
import pandas as pd
import streamlit as st

from lib.db import core_table, marts_table, run_query

BIG_FIVE = ["Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1"]
LEAGUE_OPTIONS = ["All"] + BIG_FIVE
WINDOWS = ["summer", "winter", "emergency", "All"]
TOP_N = 10


def format_fee(value):
    if value is None or value == 0:
        return "—"
    try:
        if value != value:  # NaN
            return "—"
    except TypeError:
        return "—"
    return f"€{value / 1_000_000:.1f}M"


def format_fee_axis(value):
    """Chart axis / aggregate labels — switch to billions above €1,000M."""
    if value is None or value == 0:
        return "—"
    try:
        if value != value:  # NaN
            return "—"
    except TypeError:
        return "—"
    if value >= 1_000_000_000:
        return f"€{value / 1_000_000_000:.1f}B"
    millions = value / 1_000_000
    if abs(millions - round(millions)) < 0.0001:
        return f"€{int(round(millions))}M"
    return f"€{millions:.1f}M"


FEE_AXIS_LABEL_EXPR = """
datum.value >= 1000000000
  ? '€' + format(datum.value / 1000000000, '.1f') + 'B'
  : (abs(datum.value / 1000000 - round(datum.value / 1000000)) < 0.0001
      ? '€' + format(datum.value / 1000000, 'd') + 'M'
      : '€' + format(datum.value / 1000000, '.1f') + 'M')
"""


def format_transfer_date(value) -> str:
    if value is None or (isinstance(value, float) and value != value):
        return "—"
    if isinstance(value, str) and not value.strip():
        return "—"
    try:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            ts = pd.to_datetime(value, unit="ms")
        else:
            ts = pd.to_datetime(value)
    except (ValueError, TypeError, OverflowError):
        return "—"
    if pd.isna(ts):
        return "—"
    return ts.strftime("%-d %b %Y")


st.header("Transfers")
st.caption("Top transfer fee movements across 15 competitions · 2020 to present.")

filter_col1, filter_col2, filter_col3 = st.columns(3)
with filter_col1:
    window = st.selectbox("Window", WINDOWS, index=0, key="transfers_window")
with filter_col2:
    year = st.number_input(
        "Transfer year",
        min_value=2020,
        max_value=2030,
        value=2024,
        step=1,
        key="transfers_year",
    )
with filter_col3:
    if (
        "transfers_league" not in st.session_state
        or st.session_state.transfers_league not in LEAGUE_OPTIONS
    ):
        st.session_state.transfers_league = LEAGUE_OPTIONS[0]
    league = st.selectbox("Destination league", LEAGUE_OPTIONS, key="transfers_league")

window_filter = ""
if window != "All":
    window_sql = window.replace("'", "''")
    window_filter = f"and v.transfer_window = '{window_sql}'"

league_filter = ""
if league != "All":
    league_sql = league.replace("'", "''")
    league_filter = f"and ps.league_name = '{league_sql}'"

player_season = marts_table("mart_player_season")
value_changes = marts_table("mart_player_value_changes")

sql = f"""
select
    c.team_logo_url,
    v.player_name,
    v.team_name,
    v.previous_team_name,
    v.transfer_date,
    v.transfer_fee_eur
from {value_changes} as v
left join {core_table("dim_club")} as c
    on v.team_id = c.team_id
left join (
    select
        player_id,
        team_id,
        league_season,
        max(league_name) as league_name
    from {player_season}
    group by player_id, team_id, league_season
) as ps
    on v.player_id = ps.player_id
    and v.team_id = ps.team_id
    and v.transfer_year = ps.league_season
where v.transfer_year = {year}
  and v.transfer_fee_eur is not null
{window_filter}
{league_filter}
order by v.transfer_fee_eur desc
limit {TOP_N}
"""

big_five_in_clause = ", ".join("'" + name.replace("'", "''") + "'" for name in BIG_FIVE)

by_league_sql = f"""
select
    ps.league_name,
    sum(v.transfer_fee_eur) as total_fee_eur,
    count(*) as transfers
from {value_changes} as v
left join (
    select
        player_id,
        team_id,
        league_season,
        max(league_name) as league_name
    from {player_season}
    group by player_id, team_id, league_season
) as ps
    on v.player_id = ps.player_id
    and v.team_id = ps.team_id
    and v.transfer_year = ps.league_season
where v.transfer_year = {year}
  and v.transfer_fee_eur is not null
  and ps.league_name in ({big_five_in_clause})
{window_filter}
group by ps.league_name
order by total_fee_eur desc
"""

club_spending_sql = f"""
select
    v.team_name,
    sum(v.transfer_fee_eur) as total_spend_eur
from {value_changes} as v
left join (
    select
        player_id,
        team_id,
        league_season,
        max(league_name) as league_name
    from {player_season}
    group by player_id, team_id, league_season
) as ps
    on v.player_id = ps.player_id
    and v.team_id = ps.team_id
    and v.transfer_year = ps.league_season
where v.transfer_year = {year}
  and v.transfer_fee_eur is not null
{window_filter}
{league_filter}
group by v.team_id, v.team_name
order by total_spend_eur desc
limit {TOP_N}
"""


def fee_bar_chart(chart_df):
    plot_df = chart_df.sort_values("transfer_fee_eur", ascending=True).copy()
    plot_df["fee_label"] = plot_df["transfer_fee_eur"].apply(format_fee)
    plot_df["is_top_signing"] = plot_df["transfer_fee_eur"] == plot_df["transfer_fee_eur"].max()

    chart = (
        alt.Chart(plot_df)
        .mark_bar()
        .encode(
            x=alt.X(
                "transfer_fee_eur:Q",
                title="Fee",
                axis=alt.Axis(
                    labelExpr="'€' + format(datum.value / 1000000, '.1f') + 'M'",
                ),
            ),
            y=alt.Y(
                "player_name:N",
                sort="-x",
                title="",
                axis=alt.Axis(labelLimit=0),
            ),
            color=alt.condition(
                "datum.is_top_signing",
                alt.value("#e85d04"),
                alt.value("#94a3b8"),
            ),
            tooltip=[
                alt.Tooltip("player_name:N", title="Player"),
                alt.Tooltip("fee_label:N", title="Fee"),
            ],
        )
        .properties(
            height=max(320, len(plot_df) * 28),
            padding={"left": 160, "top": 10, "right": 10, "bottom": 10},
        )
        .configure_view(strokeWidth=0)
    )
    st.altair_chart(chart, use_container_width=True)


def club_spending_chart(chart_df):
    plot_df = chart_df.sort_values("total_spend_eur", ascending=True).copy()
    plot_df["spend_label"] = plot_df["total_spend_eur"].apply(format_fee_axis)
    plot_df["is_top_spender"] = plot_df["total_spend_eur"] == plot_df["total_spend_eur"].max()

    chart = (
        alt.Chart(plot_df)
        .mark_bar()
        .encode(
            x=alt.X(
                "total_spend_eur:Q",
                title="Total spend",
                axis=alt.Axis(labelExpr=FEE_AXIS_LABEL_EXPR),
            ),
            y=alt.Y(
                "team_name:N",
                sort="-x",
                title="",
                axis=alt.Axis(labelLimit=0),
            ),
            color=alt.condition(
                "datum.is_top_spender",
                alt.value("#e85d04"),
                alt.value("#94a3b8"),
            ),
            tooltip=[
                alt.Tooltip("team_name:N", title="Club"),
                alt.Tooltip("spend_label:N", title="Total spend"),
            ],
        )
        .properties(
            height=max(320, len(plot_df) * 28),
            padding={"left": 160, "top": 10, "right": 10, "bottom": 10},
        )
        .configure_view(strokeWidth=0)
    )
    st.altair_chart(chart, use_container_width=True)


try:
    df = run_query(sql)
    by_league = run_query(by_league_sql)
    club_spending = run_query(club_spending_sql)

    largest_fee = format_fee(df["transfer_fee_eur"].iloc[0]) if len(df) > 0 else "—"
    total_fees = format_fee(float(df["transfer_fee_eur"].sum())) if len(df) > 0 else "—"

    c1, c2, c3 = st.columns(3)
    c1.metric("Top signings shown", TOP_N)
    c2.metric("Largest fee", largest_fee)
    c3.metric("Total fees", total_fees)

    if not by_league.empty and league == "All":
        st.subheader("Transfer spend by destination league (domestic)")
        st.caption(
            "Destination league reflects the club's domestic competition — not the cup or "
            "European competition the player appeared in."
        )
        league_chart_df = by_league[by_league["league_name"].isin(BIG_FIVE)].copy()
        spend_rank = league_chart_df["total_fee_eur"].astype("float64")
        league_chart_df = league_chart_df.iloc[spend_rank.argsort()[::-1]].reset_index(drop=True)
        league_chart_df["total_label"] = league_chart_df["total_fee_eur"].apply(format_fee_axis)
        league_order = league_chart_df["league_name"].tolist()
        league_chart = (
            alt.Chart(league_chart_df)
            .mark_bar()
            .encode(
                x=alt.X("league_name:N", title="League", sort=league_order),
                y=alt.Y(
                    "total_fee_eur:Q",
                    title="Fee",
                    axis=alt.Axis(labelExpr=FEE_AXIS_LABEL_EXPR),
                ),
                tooltip=[
                    alt.Tooltip("league_name:N", title="League"),
                    alt.Tooltip("total_label:N", title="Total fees"),
                    alt.Tooltip("transfers:Q", title="Transfers"),
                ],
            )
        )
        st.altair_chart(league_chart, use_container_width=True)

    if not df.empty:
        st.subheader("Top fees")
        fee_bar_chart(df[["player_name", "transfer_fee_eur"]])

    st.subheader("Club spending")
    if club_spending.empty:
        st.info(f"No club spending data for {window} {year}.")
    else:
        club_spending_chart(club_spending)
        st.caption("Total permanent fee spend — top 10 clubs by window and year.")

    st.subheader("Signings")
    if df.empty:
        st.info(f"No fee-bearing transfers for {window} {year}.")
    else:
        display_df = pd.DataFrame(
            {
                "Player": df["player_name"],
                "From": df["previous_team_name"],
                "To": df["team_name"],
                "Logo": df["team_logo_url"],
                "Date": df["transfer_date"].apply(format_transfer_date),
                "Fee": df["transfer_fee_eur"].apply(format_fee),
            }
        )

        st.dataframe(
            display_df,
            column_config={
                "Player": st.column_config.TextColumn("Player", width=150),
                "From": st.column_config.TextColumn("From", width=150),
                "To": st.column_config.TextColumn("To", width=150),
                "Logo": st.column_config.ImageColumn(" ", width="small"),
                "Date": st.column_config.TextColumn("Date", width=100),
                "Fee": st.column_config.TextColumn("Fee", width=90),
            },
            hide_index=True,
            use_container_width=True,
            height=(TOP_N * 35) + 38,
        )
except KeyError:
    st.error("Set DATABRICKS_HOST, DATABRICKS_HTTP_PATH, and DATABRICKS_TOKEN (see app/.env.example).")
except Exception as exc:  # noqa: BLE001
    st.exception(exc)
