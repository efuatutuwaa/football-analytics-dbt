"""Club domestic league season — mart_club_season + dim_club logos."""

import streamlit as st

from lib.db import core_table, marts_table, run_query

LEAGUES = ["Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1"]

st.header("Club season")
st.caption("League table standings and club statistics across the big-five domestic leagues · 2020 to present.")

filter_col1, filter_col2 = st.columns(2)
with filter_col1:
    league = st.selectbox("League", LEAGUES, index=0, key="club_season_league")
with filter_col2:
    season = st.number_input(
        "Season",
        min_value=2020,
        max_value=2030,
        value=2024,
        step=1,
        key="club_season_season",
    )

league_sql = league.replace("'", "''")

sql = f"""
select
    c.team_logo_url,
    m.team_name,
    m.matches_played,
    m.wins,
    m.draws,
    m.losses,
    m.wins * 3 + m.draws as league_points,
    m.goals_scored,
    m.goals_conceded,
    m.goal_difference,
    round((m.wins * 3 + m.draws) / nullif(m.matches_played, 0), 2) as points_per_game
from {marts_table("mart_club_season")} as m
left join {core_table("dim_club")} as c
    on m.team_id = c.team_id
where m.league_name = '{league_sql}'
  and m.league_season = {season}
order by league_points desc, m.goal_difference desc
"""


def style_league_row(row, team_count: int) -> list[str]:
    position = int(row["#"])
    relegation_start = max(team_count - 2, 1)

    if position <= 4:
        css = "background-color: rgba(100, 149, 237, 0.25)"
    elif position == 5:
        css = "background-color: rgba(255, 165, 0, 0.25)"
    elif position == 6:
        css = "background-color: rgba(147, 112, 219, 0.25)"
    elif position >= relegation_start:
        css = "background-color: rgba(220, 80, 80, 0.25)"
    else:
        css = ""

    return [css] * len(row)


try:
    df = run_query(sql)

    if df.empty:
        st.info(f"No table data for {league} {season}.")
        st.stop()

    df = df.reset_index(drop=True)
    df.insert(0, "#", df.index + 1)
    df = df.rename(
        columns={
            "team_name": "Name",
            "matches_played": "MP",
            "wins": "W",
            "draws": "D",
            "losses": "L",
            "league_points": "Pts",
            "goals_scored": "GF",
            "goals_conceded": "GA",
            "goal_difference": "GD",
            "points_per_game": "PPG",
        }
    )

    df["PPG"] = df["PPG"].astype(float).round(2)
    team_count = len(df)

    display_cols = [
        "#",
        "team_logo_url",
        "Name",
        "MP",
        "W",
        "D",
        "L",
        "Pts",
        "GF",
        "GA",
        "GD",
        "PPG",
    ]
    df = df[display_cols]

    styled = (
        df.style.apply(style_league_row, axis=1, team_count=team_count)
        .format(
            {
                "MP": "{:.0f}",
                "W": "{:.0f}",
                "D": "{:.0f}",
                "L": "{:.0f}",
                "Pts": "{:.0f}",
                "GF": "{:.0f}",
                "GA": "{:.0f}",
                "GD": "{:.0f}",
                "PPG": "{:.2f}",
            },
            na_rep="—",
        )
    )

    st.dataframe(
        styled,
        use_container_width=True,
        hide_index=True,
        column_config={
            "team_logo_url": st.column_config.ImageColumn("Club", width="small"),
        },
        height=(len(df) * 35) + 38,
    )
    st.caption(
        "🔵 Champions League · 🟠 Europa League · 🟣 Conference League · 🔴 Relegation"
    )
except KeyError as exc:
    st.error("Set DATABRICKS_HOST, DATABRICKS_HTTP_PATH, and DATABRICKS_TOKEN (see app/.env.example).")
    st.code(str(exc))
except Exception as exc:  # noqa: BLE001
    st.exception(exc)
