import os
import time
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
from databricks import sql

# ── Config ────────────────────────────────────────────────
load_dotenv()

API_KEY = os.getenv("API_FOOTBALL_KEY")
DATABRICKS_HOST = os.getenv("DATABRICKS_HOST")
DATABRICKS_HTTP_PATH = os.getenv("DATABRICKS_HTTP_PATH")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")

if not all([API_KEY, DATABRICKS_HOST, DATABRICKS_HTTP_PATH, DATABRICKS_TOKEN]):
    raise ValueError("Missing one or more env vars — check your .env file")

API_BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
ENDPOINT = "leagues"

LEAGUE_IDS = [
    39,   # Premier League
    2,    # UEFA Champions League
    1,    # World Cup
    4,    # Euros
    15,   # Club World Cup
    140,  # La Liga
    78,   # Bundesliga
    61,   # Ligue 1
    135,  # Serie A
]

SEASONS = [2020, 2021, 2022, 2023, 2024, 2025]

# ── Request counter ───────────────────────────────────────
requests_made = 0


# ── API Fetcher ───────────────────────────────────────────
def fetch_from_api(endpoint: str, params: dict = {}) -> dict:
    """Fetch data from API-Football with rate limiting."""
    global requests_made

    url = f"{API_BASE_URL}/{endpoint}"
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    requests_made += 1

    remaining = response.headers.get("x-ratelimit-requests-remaining")
    limit = response.headers.get("x-ratelimit-requests-limit")
    print(f"  API requests remaining: {remaining}/{limit}")

    if remaining and int(remaining) < 100:
        raise Exception("⚠️ API request limit almost reached — stopping!")

    time.sleep(0.5)
    return response.json()


# ── Flatten league ────────────────────────────────────────
def flatten_league(record: dict) -> dict:
    """Flatten league metadata from API response."""
    league = record.get("league", {})
    country = record.get("country", {})

    return {
        "league_id": league.get("id"),
        "league_name": league.get("name"),
        "league_type": league.get("type"),
        "league_logo_url": league.get("logo"),
        "country_name": country.get("name"),
        "country_code": country.get("code"),
        "country_flag_url": country.get("flag"),
        "ingested_at": datetime.now(tz=timezone.utc),
    }


# ── Flatten league season ─────────────────────────────────
def flatten_league_season(league_id: int, season: dict) -> dict:
    """Flatten season data from API response."""
    coverage = season.get("coverage", {})
    fixtures = coverage.get("fixtures", {})

    return {
        "league_id": league_id,
        "season_year": season.get("year"),
        "season_start": season.get("start"),
        "season_end": season.get("end"),
        "is_current_season": season.get("current"),
        "coverage_fixtures_events": fixtures.get("events"),
        "coverage_fixtures_lineups": fixtures.get("lineups"),
        "coverage_standings": coverage.get("standings"),
        "coverage_players": coverage.get("players"),
        "coverage_top_scorers": coverage.get("top_scorers"),
        "coverage_injuries": coverage.get("injuries"),
        "coverage_predictions": coverage.get("predictions"),
        "coverage_odds": coverage.get("odds"),
        "ingested_at": datetime.now(tz=timezone.utc),
    }


# ── Incremental check ─────────────────────────────────────
def get_last_ingested_at(
    cursor,
    endpoint: str,
    league_id: int = None
):
    """Get the last ingestion timestamp per endpoint and league."""
    if league_id:
        cursor.execute("""
            SELECT last_ingested_at
            FROM football_raw.ingestion_metadata
            WHERE endpoint = ?
            AND league_id = ?
            AND status = 'success'
            ORDER BY last_ingested_at DESC
            LIMIT 1
        """, [endpoint, league_id])
    else:
        cursor.execute("""
            SELECT last_ingested_at
            FROM football_raw.ingestion_metadata
            WHERE endpoint = ?
            AND status = 'success'
            ORDER BY last_ingested_at DESC
            LIMIT 1
        """, [endpoint])
    row = cursor.fetchone()
    return row[0] if row else None


# ── Update metadata ───────────────────────────────────────
def update_metadata(
    cursor,
    endpoint: str,
    rows_inserted: int,
    status: str,
    league_id: int = None
):
    """Update ingestion metadata after each run."""
    cursor.execute("""
        INSERT INTO football_raw.ingestion_metadata (
            endpoint,
            league_id,
            last_ingested_at,
            rows_inserted,
            requests_used,
            status,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [
        endpoint,
        league_id,
        datetime.now(tz=timezone.utc),
        rows_inserted,
        requests_made,
        status,
        datetime.now(tz=timezone.utc),
    ])


# ── Load leagues ──────────────────────────────────────────
def load_leagues(cursor, leagues: list) -> int:
    """Load league metadata into football_raw.raw_leagues."""
    rows_inserted = 0
    for record in leagues:
        cursor.execute("""
            INSERT INTO football_raw.raw_leagues (
                league_id,
                league_name,
                league_type,
                league_logo_url,
                country_name,
                country_code,
                country_flag_url,
                ingested_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            record["league_id"],
            record["league_name"],
            record["league_type"],
            record["league_logo_url"],
            record["country_name"],
            record["country_code"],
            record["country_flag_url"],
            record["ingested_at"],
        ])
        rows_inserted += 1
    return rows_inserted


# ── Load league seasons ───────────────────────────────────
def load_league_seasons(cursor, seasons: list) -> int:
    """Load season data into football_raw.raw_league_seasons."""
    rows_inserted = 0
    for record in seasons:
        cursor.execute("""
            INSERT INTO football_raw.raw_league_seasons (
                league_id,
                season_year,
                season_start,
                season_end,
                is_current_season,
                coverage_fixtures_events,
                coverage_fixtures_lineups,
                coverage_standings,
                coverage_players,
                coverage_top_scorers,
                coverage_injuries,
                coverage_predictions,
                coverage_odds,
                ingested_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            record["league_id"],
            record["season_year"],
            record["season_start"],
            record["season_end"],
            record["is_current_season"],
            record["coverage_fixtures_events"],
            record["coverage_fixtures_lineups"],
            record["coverage_standings"],
            record["coverage_players"],
            record["coverage_top_scorers"],
            record["coverage_injuries"],
            record["coverage_predictions"],
            record["coverage_odds"],
            record["ingested_at"],
        ])
        rows_inserted += 1
    return rows_inserted


# ── Main loader ───────────────────────────────────────────
def load_to_databricks(
    league_id: int,
    leagues: list,
    seasons: list
) -> None:
    """Load leagues and seasons into Databricks."""
    with sql.connect(
        server_hostname=DATABRICKS_HOST,
        http_path=DATABRICKS_HTTP_PATH,
        access_token=DATABRICKS_TOKEN,
        catalog="workspace"
    ) as connection:
        with connection.cursor() as cursor:

            last_ingested_at = get_last_ingested_at(
                cursor,
                ENDPOINT,
                league_id
            )

            if last_ingested_at:
                print(f"  League {league_id} already ingested at "
                      f"{last_ingested_at} — skipping")
                return

            league_rows = load_leagues(cursor, leagues)
            print(f"  ✅ Loaded {league_rows} league records")

            season_rows = load_league_seasons(cursor, seasons)
            print(f"  ✅ Loaded {season_rows} season records")

            update_metadata(
                cursor,
                ENDPOINT,
                league_rows + season_rows,
                "success",
                league_id
            )


# ── Main ──────────────────────────────────────────────────
def main():
    global requests_made
    print("🏆 Fetching leagues...")

    try:
        for league_id in LEAGUE_IDS:
            requests_made = 0  # reset per league

            print(f"\n  Fetching league {league_id}...")
            response = fetch_from_api(ENDPOINT, params={"id": league_id})
            records = response.get("response", [])

            leagues = []
            seasons = []

            for record in records:
                leagues.append(flatten_league(record))

                league_id_from_response = record.get("league", {}).get("id")
                for season in record.get("seasons", []):
                    if season.get("year") in SEASONS:
                        seasons.append(
                            flatten_league_season(
                                league_id_from_response,
                                season
                            )
                        )

            print(f"  Got {len(leagues)} league records")
            print(f"  Got {len(seasons)} season records")

            load_to_databricks(league_id, leagues, seasons)

        print("\n🎉 Leagues ingestion complete!")

    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
