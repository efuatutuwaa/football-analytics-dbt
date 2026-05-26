"""Player season stats — mart_player_season + dim_player photos."""

import altair as alt
import streamlit as st

from lib.db import core_table, marts_table, run_query

LEAGUES = ["Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1"]
TOP_N = 10

SORT_OPTIONS = {
    "Goals": {
        "sql_column": "goals",
        "chart_title": "Top scorers",
        "x_axis": "Goals",
        "primary_label": "Top goals",
        "primary_format": "int",
        "secondary_column": "goals_per_90",
        "secondary_label": "Top G/90",
        "secondary_format": "float",
    },
    "Assists": {
        "sql_column": "assists",
        "chart_title": "Top assisters",
        "x_axis": "Assists",
        "primary_label": "Top assists",
        "primary_format": "int",
        "secondary_column": "assists_per_90",
        "secondary_label": "Top A/90",
        "secondary_format": "float",
    },
    "G/90": {
        "sql_column": "goals_per_90",
        "chart_title": "Goals per 90",
        "x_axis": "G/90",
        "primary_label": "Top G/90",
        "primary_format": "float",
        "secondary_column": "goals",
        "secondary_label": "Top goals",
        "secondary_format": "int",
    },
    "A/90": {
        "sql_column": "assists_per_90",
        "chart_title": "Assists per 90",
        "x_axis": "A/90",
        "primary_label": "Top A/90",
        "primary_format": "float",
        "secondary_column": "assists",
        "secondary_label": "Top assists",
        "secondary_format": "int",
    },
}

st.header("Player season")
st.caption("Top 10 players by selected metric across the big-five domestic leagues · per competition, not blended · 2020 to present.")

filter_col1, filter_col2, filter_col3 = st.columns(3)
with filter_col1:
    league = st.selectbox("League", LEAGUES, index=0, key="player_season_league")
with filter_col2:
    season = st.number_input(
        "Season",
        min_value=2020,
        max_value=2030,
        value=2024,
        step=1,
        key="player_season_year",
    )
with filter_col3:
    sort_by = st.selectbox(
        "Sort by",
        list(SORT_OPTIONS.keys()),
        index=0,
        key="player_season_sort",
    )

sort_config = SORT_OPTIONS[sort_by]
sort_column = sort_config["sql_column"]
league_sql = league.replace("'", "''")

sql = f"""
select
    p.photo_url,
    m.player_name,
    m.team_name,
    m.appearances,
    m.goals,
    m.assists,
    m.goals_per_90,
    m.assists_per_90
from {marts_table("mart_player_season")} as m
left join {core_table("dim_player")} as p
    on m.player_id = p.player_id
where m.league_name = '{league_sql}'
  and m.league_season = {season}
order by m.{sort_column} desc, m.player_name
limit {TOP_N}
"""


def format_peak(value, peak_format: str):
    if value != value:  # NaN
        return 0 if peak_format == "int" else 0.0
    if peak_format == "int":
        return int(value)
    return round(float(value), 2)


def metric_bar_chart(chart_df, x_axis: str):
    plot_df = chart_df.sort_values("value", ascending=True).copy()
    plot_df["is_top"] = plot_df["value"] == plot_df["value"].max()

    chart = (
        alt.Chart(plot_df)
        .mark_bar()
        .encode(
            x=alt.X("value:Q", title=x_axis),
            y=alt.Y(
                "player_name:N",
                sort="-x",
                title="",
                axis=alt.Axis(labelLimit=0),
            ),
            color=alt.condition(
                "datum.is_top",
                alt.value("#e85d04"),
                alt.value("#94a3b8"),
            ),
            tooltip=["player_name", alt.Tooltip("value:Q", title=x_axis, format=".2f")],
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

    peak_value = format_peak(
        df[sort_column].max() if len(df) > 0 else 0,
        sort_config["primary_format"],
    )
    secondary_value = format_peak(
        df[sort_config["secondary_column"]].max() if len(df) > 0 else 0,
        sort_config["secondary_format"],
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Top players shown", TOP_N)
    c2.metric(sort_config["primary_label"], peak_value)
    c3.metric(sort_config["secondary_label"], secondary_value)

    if not df.empty:
        st.subheader(sort_config["chart_title"])
        chart_df = df[["player_name", sort_column]].copy()
        chart_df.columns = ["player_name", "value"]
        metric_bar_chart(chart_df, sort_config["x_axis"])

    st.subheader("Leaderboard")
    if df.empty:
        st.info(f"No player data for {league} {season}.")
    else:
        renamed = df.rename(
            columns={
                "photo_url": "Player",
                "player_name": "Name",
                "team_name": "Club",
                "appearances": "Apps",
                "goals": "Goals",
                "assists": "Assists",
                "goals_per_90": "G/90",
                "assists_per_90": "A/90",
            }
        )
        display_df = renamed[
            ["Player", "Name", "Club", "Apps", "Goals", "Assists", "G/90", "A/90"]
        ]
        st.dataframe(
            display_df,
            column_config={
                "Player": st.column_config.ImageColumn("Player", width=50),
                "Name": st.column_config.TextColumn("Name", width=140),
                "Club": st.column_config.TextColumn("Club", width=120),
                "Apps": st.column_config.NumberColumn("Apps", width=55),
                "Goals": st.column_config.NumberColumn("Goals", width=65),
                "Assists": st.column_config.NumberColumn("Assists", width=75),
                "G/90": st.column_config.NumberColumn("G/90", width=65, format="%.2f"),
                "A/90": st.column_config.NumberColumn("A/90", width=65, format="%.2f"),
            },
            hide_index=True,
            use_container_width=True,
            height=(len(display_df) * 35) + 38,
        )
except KeyError:
    st.error("Set DATABRICKS_HOST, DATABRICKS_HTTP_PATH, and DATABRICKS_TOKEN (see app/.env.example).")
except Exception as exc:  # noqa: BLE001
    st.exception(exc)
