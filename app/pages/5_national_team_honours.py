"""International podium — mart_national_team_honours + dim_national_team flags."""

import altair as alt
import pandas as pd
import streamlit as st

from lib.db import core_table, marts_table, run_query

PODIUM_TABLE_COLUMNS = {
    "Flag": st.column_config.ImageColumn(" ", width="small"),
    "Nation": st.column_config.TextColumn("Nation", width=120),
    "Tournament": st.column_config.TextColumn("Tournament", width=160),
    "Season": st.column_config.NumberColumn("Season", width=75, format="%d"),
    "Placement": st.column_config.TextColumn("Placement", width=110),
    "GF": st.column_config.NumberColumn("GF", width=60),
    "GA": st.column_config.NumberColumn("GA", width=60),
}

st.header("National team honours")
st.caption("World Cup and European Championship podium finishes · 2020 to present.")

tournament = st.selectbox(
    "Tournament",
    ["All", "FIFA World Cup", "UEFA European Championship"],
    index=0,
)
season = st.number_input("Tournament year", min_value=2020, max_value=2030, value=2024, key="nt_honours_season")

tournament_clause = ""
if tournament == "FIFA World Cup":
    tournament_clause = "and m.league_id = 1"
elif tournament == "UEFA European Championship":
    tournament_clause = "and m.league_id = 4"

podium_select = """
    coalesce(n.country_flag_url, n.team_logo_url) as nation_flag_url,
    m.team_name,
    m.league_name,
    m.league_season,
    m.tournament_placement,
    m.goals_scored,
    m.goals_conceded
"""

podium_from = f"""
from {marts_table("mart_national_team_honours")} as m
left join {core_table("dim_national_team")} as n
    on m.team_id = n.team_id
"""

podium_order = """
order by
    case m.tournament_placement
        when 'Winner' then 1
        when 'Runner-up' then 2
        else 3
    end,
    m.team_name
"""

winners_sql = f"""
select
    {podium_select}
{podium_from}
where m.league_season = {season}
{tournament_clause}
{podium_order}
"""

history_sql = f"""
select
    {podium_select}
{podium_from}
where m.league_season >= 2020
{tournament_clause}
order by
    m.league_season desc,
    case m.tournament_placement
        when 'Winner' then 1
        when 'Runner-up' then 2
        else 3
    end,
    m.team_name
"""


def build_podium_display_df(raw_df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Flag": raw_df["nation_flag_url"],
            "Nation": raw_df["team_name"],
            "Tournament": raw_df["league_name"],
            "Season": raw_df["league_season"],
            "Placement": raw_df["tournament_placement"],
            "GF": raw_df["goals_scored"],
            "GA": raw_df["goals_conceded"],
        }
    )


def goals_podium_chart(podium_df: pd.DataFrame) -> None:
    chart_df = podium_df.copy()
    gf_rank = chart_df["goals_scored"].astype("float64")
    chart_df = chart_df.iloc[gf_rank.argsort()[::-1]].reset_index(drop=True)
    nation_order = chart_df["team_name"].tolist()

    long_df = chart_df.melt(
        id_vars=["team_name"],
        value_vars=["goals_scored", "goals_conceded"],
        var_name="metric",
        value_name="goals",
    )
    long_df["metric"] = long_df["metric"].map(
        {"goals_scored": "GF", "goals_conceded": "GA"}
    )

    chart = (
        alt.Chart(long_df)
        .mark_bar()
        .encode(
            x=alt.X("goals:Q", title="Goals"),
            y=alt.Y("team_name:N", title="", sort=nation_order, axis=alt.Axis(labelLimit=0)),
            color=alt.Color(
                "metric:N",
                title="",
                scale=alt.Scale(domain=["GF", "GA"], range=["#e85d04", "#64748b"]),
                legend=alt.Legend(title=""),
            ),
            xOffset=alt.XOffset("metric:N"),
            tooltip=[
                alt.Tooltip("team_name:N", title="Nation"),
                alt.Tooltip("metric:N", title=""),
                alt.Tooltip("goals:Q", title="Goals"),
            ],
        )
        .properties(
            height=max(280, len(nation_order) * 36),
            padding={"left": 120, "top": 10, "right": 10, "bottom": 10},
        )
        .configure_view(strokeWidth=0)
    )
    st.altair_chart(chart, use_container_width=True)


try:
    podium = run_query(winners_sql)
    history = run_query(history_sql)

    c1, c2, c3 = st.columns(3)
    c1.metric("Nations on podium", len(podium))
    winners_count = 0
    if len(podium) > 0:
        winners_count = int((podium["tournament_placement"] == "Winner").sum())
    c2.metric("Winners this edition", winners_count)
    c3.metric("Goals scored (edition total)", int(podium["goals_scored"].sum()) if len(podium) > 0 else 0)

    if not podium.empty:
        st.subheader(f"Podium — {season}")
        display_df = build_podium_display_df(podium)
        st.dataframe(
            display_df,
            column_config=PODIUM_TABLE_COLUMNS,
            hide_index=True,
            use_container_width=True,
            height=(len(display_df) * 35) + 38,
        )

        st.subheader("Goals — podium nations")
        goals_podium_chart(podium)

    st.subheader("Podium history")
    if history.empty:
        st.info(f"No podium history for {tournament}.")
    else:
        history_df = build_podium_display_df(history)
        st.dataframe(
            history_df,
            column_config=PODIUM_TABLE_COLUMNS,
            hide_index=True,
            use_container_width=True,
            height=(len(history_df) * 35) + 38,
        )
except KeyError:
    st.error("Set DATABRICKS_HOST, DATABRICKS_HTTP_PATH, and DATABRICKS_TOKEN (see app/.env.example).")
except Exception as exc:  # noqa: BLE001
    st.exception(exc)
