"""Squad fee footprint — mart_club_squad_value + dim_club logos."""

import altair as alt
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib.db import core_table, marts_table, run_query
from lib.formatting import format_fee

FEE_AXIS_LABEL_EXPR = """
datum.value >= 1000000000
  ? '€' + format(datum.value / 1000000000, '.1f') + 'B'
  : (abs(datum.value / 1000000 - round(datum.value / 1000000)) < 0.0001
      ? '€' + format(datum.value / 1000000, 'd') + 'M'
      : '€' + format(datum.value / 1000000, '.1f') + 'M')
"""

st.header("Club squad value")
st.caption(
    "Estimated squad fee footprint based on transfer fees paid — not official market valuation."
)

league = st.selectbox(
    "League",
    ["Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1"],
    index=0,
)
season = st.number_input("Season", min_value=2020, max_value=2030, value=2024, key="squad_value_season")

league_sql = league.replace("'", "''")

sql = f"""
select
    c.team_logo_url,
    m.team_name,
    m.squad_estimated_fee_eur,
    m.avg_estimated_fee_eur_per_player,
    m.inbound_spend_in_season_eur,
    m.max_inbound_fee_eur
from {marts_table("mart_club_squad_value")} as m
left join {core_table("dim_club")} as c
    on m.team_id = c.team_id
where m.league_name = '{league_sql}'
  and m.league_season = {season}
order by m.squad_estimated_fee_eur desc nulls last, m.team_name
"""

trend_sql = f"""
select
    m.team_name,
    m.league_season,
    m.squad_estimated_fee_eur
from {marts_table("mart_club_squad_value")} as m
where m.league_name = '{league_sql}'
  and m.squad_estimated_fee_eur is not null
order by m.team_name, m.league_season
"""


def squad_value_chart(chart_df):
    plot_df = chart_df.sort_values("squad_estimated_fee_eur", ascending=True).copy()
    plot_df["value_label"] = plot_df["squad_estimated_fee_eur"].apply(format_fee)
    plot_df["is_top_club"] = plot_df["squad_estimated_fee_eur"] == plot_df["squad_estimated_fee_eur"].max()

    chart = (
        alt.Chart(plot_df)
        .mark_bar()
        .encode(
            x=alt.X(
                "squad_estimated_fee_eur:Q",
                title="Squad value",
                axis=alt.Axis(labelExpr=FEE_AXIS_LABEL_EXPR),
            ),
            y=alt.Y(
                "team_name:N",
                sort="-x",
                title="",
                axis=alt.Axis(labelLimit=0),
            ),
            color=alt.condition(
                "datum.is_top_club",
                alt.value("#e85d04"),
                alt.value("#94a3b8"),
            ),
            tooltip=[
                alt.Tooltip("team_name:N", title="Club"),
                alt.Tooltip("value_label:N", title="Squad value"),
            ],
        )
        .properties(
            height=max(320, len(plot_df) * 28),
            padding={"left": 160, "top": 10, "right": 10, "bottom": 10},
        )
        .configure_view(strokeWidth=0)
    )
    st.altair_chart(chart, use_container_width=True)


def squad_value_trend_chart(chart_df):
    plot_df = chart_df.sort_values("league_season").copy()
    plot_df["squad_value_millions"] = plot_df["squad_estimated_fee_eur"].astype("float64") / 1_000_000
    plot_df["value_label"] = plot_df["squad_estimated_fee_eur"].apply(format_fee)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=plot_df["league_season"],
            y=plot_df["squad_value_millions"],
            mode="lines+markers",
            line=dict(color="#4a90d9", width=2.5),
            marker=dict(size=8, color="#4a90d9"),
            hovertemplate="<b>%{x}</b><br>Squad value: %{customdata}<extra></extra>",
            customdata=plot_df["value_label"],
        )
    )
    fig.update_layout(
        xaxis=dict(title="Season", tickmode="linear", dtick=1),
        yaxis=dict(title="Squad value", tickformat=",.0f"),
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=20, b=20),
        height=360,
    )
    fig.update_yaxes(tickprefix="€", ticksuffix="M")

    st.plotly_chart(fig, use_container_width=True)


try:
    df = run_query(sql)
    trend_df = run_query(trend_sql)

    c1, c2, c3 = st.columns(3)
    c1.metric("Clubs", len(df))
    total_squad = float(df["squad_estimated_fee_eur"].sum()) if len(df) > 0 else 0.0
    top_val = float(df["squad_estimated_fee_eur"].iloc[0]) if len(df) > 0 else 0.0
    if len(df) > 0 and df["squad_estimated_fee_eur"].iloc[0] != df["squad_estimated_fee_eur"].iloc[0]:
        top_val = 0.0
    c2.metric("Total estimated", format_fee(total_squad))
    c3.metric("Top club", format_fee(top_val))

    if not df.empty:
        chart_df = df[["team_name", "squad_estimated_fee_eur"]].dropna()
        if len(chart_df) > 0:
            st.subheader("Estimated squad value")
            squad_value_chart(chart_df)

    if not trend_df.empty:
        club_options = sorted(trend_df["team_name"].unique().tolist())
        default_club = (
            df["team_name"].iloc[0]
            if not df.empty and df["team_name"].iloc[0] in club_options
            else club_options[0]
        )
        if (
            "squad_value_trend_club" not in st.session_state
            or st.session_state.squad_value_trend_club not in club_options
        ):
            st.session_state.squad_value_trend_club = default_club
        selected_club = st.selectbox("Club", club_options, key="squad_value_trend_club")
        club_trend = trend_df[trend_df["team_name"] == selected_club].copy()

        st.subheader(f"{selected_club} — squad value trend")
        if club_trend.empty:
            st.info(f"No squad value trend data for {selected_club}.")
        else:
            squad_value_trend_chart(club_trend)

        season_ints: list[int] = []
        for raw_season in trend_df["league_season"].tolist():
            try:
                if raw_season is None or (isinstance(raw_season, float) and raw_season != raw_season):
                    continue
                season_ints.append(int(raw_season))
            except (TypeError, ValueError):
                continue
        if season_ints:
            max_season = max(season_ints)
            st.info(
                f"⚠️ The {max_season} summer transfer window has not yet opened. "
                f"Squad values shown for {max_season} reflect fees paid to date — "
                "values will increase as clubs make summer signings."
            )
        st.caption("Estimated fee footprint based on cumulative transfer fees paid per season.")

    st.subheader("By club")
    if df.empty:
        st.info(f"No squad value data for {league} {season}.")
    else:
        display_df = pd.DataFrame(
            {
                "Logo": df["team_logo_url"],
                "Club": df["team_name"],
                "Squad value": df["squad_estimated_fee_eur"].apply(format_fee),
                "Avg per player": df["avg_estimated_fee_eur_per_player"].apply(format_fee),
                "Season spend": df["inbound_spend_in_season_eur"].apply(
                    lambda value: format_fee(value, zero_as_missing=False)
                ),
                "Top signing": df["max_inbound_fee_eur"].apply(format_fee),
            }
        )
        st.dataframe(
            display_df,
            column_config={
                "Logo": st.column_config.ImageColumn(" ", width="small"),
                "Club": st.column_config.TextColumn("Club", width=140),
                "Squad value": st.column_config.TextColumn("Squad value", width=110),
                "Avg per player": st.column_config.TextColumn("Avg per player", width=110),
                "Season spend": st.column_config.TextColumn("Season spend", width=110),
                "Top signing": st.column_config.TextColumn("Top signing", width=110),
            },
            hide_index=True,
            use_container_width=True,
            height=(len(display_df) * 35) + 38,
        )
except KeyError:
    st.error("Set DATABRICKS_HOST, DATABRICKS_HTTP_PATH, and DATABRICKS_TOKEN (see app/.env.example).")
except Exception as exc:  # noqa: BLE001
    st.exception(exc)
