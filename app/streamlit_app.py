"""Football analytics — Streamlit entrypoint. Run: streamlit run streamlit_app.py (from app/)."""

from pathlib import Path

from dotenv import load_dotenv
import streamlit as st

load_dotenv(Path(__file__).resolve().parent / ".env")

st.set_page_config(
    page_title="Football Analytics Platform · Efua Tutuwaa",
    page_icon="⚽",
    layout="wide",
)

PAGES = [
    (
        "Club season",
        "mart_club_season",
        "How did a club finish across the league table for a given season?",
    ),
    (
        "Player season",
        "mart_player_season",
        "Full season stats per player, per competition, not blended across cup and league.",
    ),
    (
        "European club",
        "mart_club_european_performance",
        "UCL and CWC campaigns by round, using official UEFA round labels.",
    ),
    (
        "Transfers",
        "mart_player_value_changes",
        "Permanent fee moves by destination league, denominated in EUR.",
    ),
    (
        "Club honours",
        "mart_club_honours",
        "Trophy cabinet with correct handling of trebles and doubles.",
    ),
    (
        "National team honours",
        "mart_national_team_honours",
        "World Cup and Euros podium finishes by nation.",
    ),
    (
        "Club squad value",
        "mart_club_squad_value",
        "Estimated squad fee footprint by club and season.",
    ),
    (
        "Ops pipeline",
        "mart_pipeline_health + mart_api_usage",
        "Last night's ingest health and API quota consumption.",
    ),
]

st.title("Football Analytics Platform · Efua Tutuwaa")
st.markdown(
    "An analytical application built on **football_marts** and **football_core** — "
    "8 pages, 15 competitions, 41,000+ players tracked across 2020 to present."
)

stat_cols = st.columns(4)
stat_cols[0].metric("Competitions", "15")
stat_cols[1].metric("Players", "41,000+")
stat_cols[2].metric("Marts", "18")
stat_cols[3].metric("Seasons", "2020→")

st.subheader("Pages")

for row_start in range(0, len(PAGES), 2):
    left_col, right_col = st.columns(2)
    for col, page in zip([left_col, right_col], PAGES[row_start : row_start + 2]):
        title, mart, description = page
        with col:
            with st.container(border=True):
                st.markdown(f"**{title}**")
                st.caption(mart)
                st.write(description)

st.markdown(
    "**Docs:** "
    "[architecture.md](https://github.com/efuatutuwaa/football-analytics-dbt/blob/main/docs/architecture.md) · "
    "[case-study.md](https://github.com/efuatutuwaa/football-analytics-dbt/blob/main/docs/case-study.md) · "
    "[data-catalog.md](https://github.com/efuatutuwaa/football-analytics-dbt/blob/main/docs/data-catalog.md)"
)
