"""Club trophy cabinet — mart_club_honours + dim_club logos."""

import pandas as pd
import streamlit as st

from lib.db import core_table, marts_table, run_query

LEAGUES = ["Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1"]
LEAGUE_OPTIONS = ["All"] + LEAGUES

st.header("Club honours")
st.caption("League titles, domestic cups and European trophies per club-season.")

filter_col1, filter_col2 = st.columns(2)
with filter_col1:
    if (
        "club_honours_league" not in st.session_state
        or st.session_state.club_honours_league not in LEAGUE_OPTIONS
    ):
        st.session_state.club_honours_league = LEAGUE_OPTIONS[0]
    league = st.selectbox("League", LEAGUE_OPTIONS, key="club_honours_league")
with filter_col2:
    season = st.number_input(
        "Season",
        min_value=2020,
        max_value=2030,
        value=2024,
        step=1,
        key="club_honours_season",
    )

league_join = ""
league_filter = ""
if league != "All":
    league_sql = league.replace("'", "''")
    league_join = f"""
inner join {marts_table("mart_club_season")} as cs
    on m.team_id = cs.team_id
    and m.league_season = cs.league_season
"""
    league_filter = f"and cs.league_name = '{league_sql}'"

detail_sql = f"""
select
    c.team_logo_url,
    m.team_name,
    m.league_season,
    m.league_titles_won,
    m.domestic_cups_won,
    m.european_trophies_won,
    m.total_trophies,
    m.honour_label
from {marts_table("mart_club_honours")} as m
{league_join}
left join {core_table("dim_club")} as c
    on m.team_id = c.team_id
where m.league_season = {season}
{league_filter}
order by m.total_trophies desc, m.team_name
"""

try:
    detail = run_query(detail_sql)

    c1, c2, c3 = st.columns(3)
    c1.metric("Club-seasons with trophies", len(detail))
    trebles = 0
    if len(detail) > 0:
        trebles = int((detail["honour_label"] == "Treble").sum())
    c2.metric("Trebles", trebles)
    c3.metric("Total trophies", int(detail["total_trophies"].sum()) if len(detail) > 0 else 0)

    st.subheader("Trophy cabinet")
    if detail.empty:
        st.info(f"No trophy data for {league} {season}.")
    else:
        display_df = pd.DataFrame(
            {
                "Club": detail["team_logo_url"],
                "Name": detail["team_name"],
                "Season": detail["league_season"],
                "League titles": detail["league_titles_won"],
                "Domestic cups": detail["domestic_cups_won"],
                "European trophies": detail["european_trophies_won"],
                "Total": detail["total_trophies"],
                "Achievement": detail["honour_label"],
            }
        )
        display_df["Achievement"] = display_df["Achievement"].fillna("—")
        st.dataframe(
            display_df,
            column_config={
                "Club": st.column_config.ImageColumn(" ", width="small"),
                "Name": st.column_config.TextColumn("Club", width=160),
                "Season": st.column_config.NumberColumn("Season", width=70, format="%d"),
                "League titles": st.column_config.NumberColumn("L. titles", width=80),
                "Domestic cups": st.column_config.NumberColumn("Dom. cups", width=80),
                "European trophies": st.column_config.NumberColumn("Euro. trophies", width=100),
                "Total": st.column_config.NumberColumn("Total", width=60),
                "Achievement": st.column_config.TextColumn("Achievement", width=100),
            },
            hide_index=True,
            use_container_width=True,
            height=(len(display_df) * 35) + 38,
        )
except KeyError:
    st.error("Set DATABRICKS_HOST, DATABRICKS_HTTP_PATH, and DATABRICKS_TOKEN (see app/.env.example).")
except Exception as exc:  # noqa: BLE001
    st.exception(exc)
