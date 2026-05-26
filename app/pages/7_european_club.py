"""European club campaigns — mart_club_european_performance + dim_club logos."""

import altair as alt
import pandas as pd
import streamlit as st

from lib.db import core_table, marts_table, run_query

TOP_N = 10

st.header("European club performance")
st.caption(
    "UEFA Champions League and Club World Cup campaigns · main tournament matches only · "
    "2020 to present."
)

_competitions = {
    "UEFA Champions League": 2,
    "FIFA Club World Cup": 15,
}
competition = st.selectbox("Competition", list(_competitions.keys()), index=0)
league_id = _competitions[competition]
season = st.number_input("Season", min_value=2020, max_value=2030, value=2024, key="european_season")
winners_only = st.checkbox("Tournament winners only", value=False)

winner_clause = "and m.was_tournament_winner = true" if winners_only else ""

sql = f"""
select
    c.team_logo_url,
    m.team_name,
    m.matches_played,
    m.wins,
    m.draws,
    m.losses,
    m.goals_scored,
    m.goals_conceded,
    m.farthest_round,
    m.group_position,
    m.group_points,
    m.was_tournament_winner
from {marts_table("mart_club_european_performance")} as m
left join {core_table("dim_club")} as c
    on m.team_id = c.team_id
where m.league_id = {league_id}
  and m.league_season = {season}
{winner_clause}
order by m.farthest_round_order desc, m.goals_scored desc, m.team_name
"""

chart_sql = f"""
select
    m.team_name,
    m.goals_scored
from {marts_table("mart_club_european_performance")} as m
where m.league_id = {league_id}
  and m.league_season = {season}
order by m.goals_scored desc
limit {TOP_N}
"""


def goals_bar_chart(chart_df):
    plot_df = chart_df.sort_values("goals_scored", ascending=True).copy()
    plot_df["is_top"] = plot_df["goals_scored"] == plot_df["goals_scored"].max()

    chart = (
        alt.Chart(plot_df)
        .mark_bar()
        .encode(
            x=alt.X("goals_scored:Q", title="Goals"),
            y=alt.Y(
                "team_name:N",
                sort="-x",
                title="",
                axis=alt.Axis(labelLimit=0),
            ),
            color=alt.condition(
                "datum.is_top",
                alt.value("#e85d04"),
                alt.value("#94a3b8"),
            ),
            tooltip=[
                alt.Tooltip("team_name:N", title="Club"),
                alt.Tooltip("goals_scored:Q", title="Goals"),
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
    chart_df = run_query(chart_sql)

    knockout_rounds = ["Quarter-finals", "Semi-finals", "Final", "Winner"]
    qf_df = df[df["farthest_round"].isin(knockout_rounds)]

    c1, c2, c3 = st.columns(3)
    c1.metric("Clubs — QF or further", len(qf_df))
    c2.metric("Winners", int(df["was_tournament_winner"].sum()) if len(df) else 0)
    c3.metric("Goals scored", int(df["goals_scored"].sum()) if len(df) else 0)

    if not chart_df.empty:
        st.subheader(f"Goals by club — top {TOP_N}")
        goals_bar_chart(chart_df)

    st.subheader("Campaign summary")
    if qf_df.empty:
        st.info(f"No clubs reached the Quarter-finals or further in {competition} {season}.")
    else:
        summary_df = pd.DataFrame(
            {
                "Logo": qf_df["team_logo_url"],
                "Club": qf_df["team_name"],
                "MP": qf_df["matches_played"],
                "W": qf_df["wins"],
                "D": qf_df["draws"],
                "L": qf_df["losses"],
                "GF": qf_df["goals_scored"],
                "GA": qf_df["goals_conceded"],
                "Farthest round": qf_df["farthest_round"],
                "League pos": qf_df["group_position"],
                "League pts": qf_df["group_points"],
            }
        )
        st.dataframe(
            summary_df,
            column_config={
                "Logo": st.column_config.ImageColumn(" ", width="small"),
                "Club": st.column_config.TextColumn("Club", width=160),
                "MP": st.column_config.NumberColumn("MP", width=55),
                "W": st.column_config.NumberColumn("W", width=50),
                "D": st.column_config.NumberColumn("D", width=50),
                "L": st.column_config.NumberColumn("L", width=50),
                "GF": st.column_config.NumberColumn("GF", width=55),
                "GA": st.column_config.NumberColumn("GA", width=55),
                "Farthest round": st.column_config.TextColumn("Farthest round", width=160),
                "League pos": st.column_config.NumberColumn("League pos", width=85),
                "League pts": st.column_config.NumberColumn("League pts", width=85),
            },
            hide_index=True,
            use_container_width=True,
            height=(len(summary_df) * 35) + 38,
        )
        st.caption("Showing clubs who reached the Quarter-finals or further.")

    if not df.empty:
        club = st.selectbox("Match breakdown by round", df["team_name"].tolist())
        safe_club = str(club).replace("'", "''")
        round_sql = f"""
        select
            f.league_round_display as round,
            count(*) as matches,
            sum(case when f.is_winner then 1 else 0 end) as wins,
            sum(f.goals_scored) as goals_scored,
            sum(f.goals_conceded) as goals_conceded
        from {core_table("fact_club_intl_run")} as f
        inner join {marts_table("mart_club_european_performance")} as m
            on f.team_id = m.team_id
            and f.league_id = m.league_id
            and f.league_season = m.league_season
        where m.league_name = '{competition}'
          and m.league_season = {season}
          and m.team_name = '{safe_club}'
          and f.match_status_short in ('FT', 'AET', 'PEN')
          and coalesce(f.league_round, '') not like '%Qualifying%'
          and coalesce(f.league_round, '') not like 'Preliminary%'
        group by f.league_round_display
        order by max(f.round_order), f.league_round_display
        """
        rounds = run_query(round_sql)
        with st.expander(f"Rounds played — {club}", expanded=True):
            if rounds.empty:
                st.info(f"No rounds data for {club}.")
            else:
                rounds_display = pd.DataFrame(
                    {
                        "Round": rounds["round"],
                        "MP": rounds["matches"],
                        "W": rounds["wins"],
                        "GF": rounds["goals_scored"],
                        "GA": rounds["goals_conceded"],
                    }
                )
                st.dataframe(
                    rounds_display,
                    column_config={
                        "Round": st.column_config.TextColumn("Round", width=200),
                        "MP": st.column_config.NumberColumn("MP", width=60),
                        "W": st.column_config.NumberColumn("W", width=55),
                        "GF": st.column_config.NumberColumn("GF", width=60),
                        "GA": st.column_config.NumberColumn("GA", width=60),
                    },
                    hide_index=True,
                    use_container_width=True,
                    height=(len(rounds_display) * 35) + 38,
                )
                st.caption(f"Total from breakdown: {int(rounds['matches'].sum())} matches")
except KeyError:
    st.error("Set DATABRICKS_HOST, DATABRICKS_HTTP_PATH, and DATABRICKS_TOKEN (see app/.env.example).")
except Exception as exc:  # noqa: BLE001
    st.exception(exc)
