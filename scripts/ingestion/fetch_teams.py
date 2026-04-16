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
ENDPOINT = "teams"

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


# ── Flatten team ──────────────────────────────────────────
def flatten_team(record: dict) -> dict:
    """Flatten team metadata from API response."""
    team = record.get("team", {})

    return {
        "team_id": team.get("id"),
        "team_name": team.get("name"),
        "team_code": team.get("code"),
        "team_country": team.get("country"),
        "founded_year": team.get("founded"),
        "is_national_team": team.get("national"),
        "team_logo_url": team.get("logo"),
        "ingested_at": datetime.now(tz=timezone.utc),
    }


# ── Flatten venue ─────────────────────────────────────────
def flatten_venue(record: dict) -> dict:
    """Flatten venue metadata from API response."""
    venue = record.get("venue", {})

    return {
        "venue_id": venue.get("id"),
        "venue_name": venue.get("name"),
        "venue_address": venue.get("address"),
        "venue_city": venue.get("city"),
        "venue_capacity": venue.get("capacity"),
        "venue_surface": venue.get("surface"),
        "venue_image_url": venue.get("image"),
        "ingested_at": datetime.now(tz=timezone.utc),
    }


# ── Flatten team season ───────────────────────────────────
def flatten_team_season(
    team_id: int,
    league_id: int,
    season: int
) -> dict:
    """Flatten team season membership."""
    return {
        "team_id": team_id,
        "league_id": league_id,
        "season_year": season,
        "ingested_at": datetime.now(tz=timezone.utc),
    }


# ── Incremental check ─────────────────────────────────────
def get_last_ingested_at(
    cursor,
    endpoint: str,
    entity_id: int = None
):
    """Get the last ingestion timestamp per endpoint and entity."""
    if entity_id:
        cursor.execute("""
            SELECT last_ingested_at
            FROM football_raw.ingestion_metadata
            WHERE endpoint = ?
            AND entity_id = ?
            AND status IN ('success', 'skipped')
            ORDER BY last_ingested_at DESC
            LIMIT 1
        """, [endpoint, entity_id])
    else:
        cursor.execute("""
            SELECT last_ingested_at
            FROM football_raw.ingestion_metadata
            WHERE endpoint = ?
            AND status IN ('success', 'skipped')
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
    entity_id: int = None
):
    """Update ingestion metadata after each run."""
    cursor.execute("""
        INSERT INTO football_raw.ingestion_metadata (
            endpoint,
            entity_id,
            last_ingested_at,
            rows_inserted,
            requests_used,
            status,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [
        endpoint,
        entity_id,
        datetime.now(tz=timezone.utc),
        rows_inserted,
        requests_made,
        status,
        datetime.now(tz=timezone.utc),
    ])


# ── Load teams ────────────────────────────────────────────
def load_teams(cursor, teams: list) -> int:
    """Load unique team metadata into football_raw.raw_teams."""
    rows_inserted = 0
    for record in teams:
        # check if team already exists
        cursor.execute("""
            SELECT COUNT(*)
            FROM football_raw.raw_teams
            WHERE team_id = ?
        """, [record["team_id"]])
        exists = cursor.fetchone()[0] > 0

        if exists:
            continue

        cursor.execute("""
            INSERT INTO football_raw.raw_teams (
                team_id,
                team_name,
                team_code,
                team_country,
                founded_year,
                is_national_team,
                team_logo_url,
                ingested_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            record["team_id"],
            record["team_name"],
            record["team_code"],
            record["team_country"],
            record["founded_year"],
            record["is_national_team"],
            record["team_logo_url"],
            record["ingested_at"],
        ])
        rows_inserted += 1
    return rows_inserted


# ── Load venues ───────────────────────────────────────────
def load_venues(cursor, venues: list) -> int:
    """Load unique venue metadata into football_raw.raw_venues."""
    rows_inserted = 0
    for record in venues:
        if not record["venue_id"]:
            continue

        # check if venue already exists
        cursor.execute("""
            SELECT COUNT(*)
            FROM football_raw.raw_venues
            WHERE venue_id = ?
        """, [record["venue_id"]])
        exists = cursor.fetchone()[0] > 0

        if exists:
            continue

        cursor.execute("""
            INSERT INTO football_raw.raw_venues (
                venue_id,
                venue_name,
                venue_address,
                venue_city,
                venue_capacity,
                venue_surface,
                venue_image_url,
                ingested_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            record["venue_id"],
            record["venue_name"],
            record["venue_address"],
            record["venue_city"],
            record["venue_capacity"],
            record["venue_surface"],
            record["venue_image_url"],
            record["ingested_at"],
        ])
        rows_inserted += 1
    return rows_inserted


# ── Load team seasons ─────────────────────────────────────
def load_team_seasons(cursor, team_seasons: list) -> int:
    """Load team season membership into football_raw.raw_team_seasons."""
    rows_inserted = 0
    for record in team_seasons:
        cursor.execute("""
            INSERT INTO football_raw.raw_team_seasons (
                team_id,
                league_id,
                season_year,
                ingested_at
            ) VALUES (?, ?, ?, ?)
        """, [
            record["team_id"],
            record["league_id"],
            record["season_year"],
            record["ingested_at"],
        ])
        rows_inserted += 1
    return rows_inserted


# ── Main loader ───────────────────────────────────────────
def load_to_databricks(
    league_id: int,
    season: int,
    teams: list,
    venues: list,
    team_seasons: list
) -> None:
    """Load teams, venues and team seasons into Databricks."""
    with sql.connect(
        server_hostname=DATABRICKS_HOST,
        http_path=DATABRICKS_HTTP_PATH,
        access_token=DATABRICKS_TOKEN,
        catalog="workspace"
    ) as connection:
        with connection.cursor() as cursor:

            team_rows = load_teams(cursor, teams)
            print(f"  ✅ Loaded {team_rows} new teams")

            venue_rows = load_venues(cursor, venues)
            print(f"  ✅ Loaded {venue_rows} new venues")

            season_rows = load_team_seasons(cursor, team_seasons)
            print(f"  ✅ Loaded {season_rows} team season records")

            update_metadata(
                cursor,
                f"{ENDPOINT}_{season}",
                team_rows + venue_rows + season_rows,
                "success",
                league_id
            )


# ── Main ──────────────────────────────────────────────────
def main():
    global requests_made
    print("⚽ Fetching teams...")

    try:
        for league_id in LEAGUE_IDS:
            for season in SEASONS:
                requests_made = 0

                # ── incremental check before API call ──
                with sql.connect(
                    server_hostname=DATABRICKS_HOST,
                    http_path=DATABRICKS_HTTP_PATH,
                    access_token=DATABRICKS_TOKEN,
                    catalog="workspace"
                ) as connection:
                    with connection.cursor() as cursor:
                        last_ingested_at = get_last_ingested_at(
                            cursor,
                            f"{ENDPOINT}_{season}",
                            league_id
                        )

                if last_ingested_at:
                    print(f"  League {league_id} season {season} "
                          f"already ingested — skipping")
                    continue

                print(f"\n  Fetching teams for league "
                      f"{league_id} season {season}...")

                response = fetch_from_api(
                    ENDPOINT,
                    params={"league": league_id, "season": season}
                )
                records = response.get("response", [])

                if not records:
                    print(f"  No teams found for league {league_id} "
                          f"season {season} — skipping")
                    continue

                teams = [flatten_team(r) for r in records]
                venues = [flatten_venue(r) for r in records]
                team_seasons = [
                    flatten_team_season(
                        r.get("team", {}).get("id"),
                        league_id,
                        season
                    )
                    for r in records
                ]

                print(f"  Got {len(teams)} teams")

                load_to_databricks(
                    league_id,
                    season,
                    teams,
                    venues,
                    team_seasons
                )

        print("\n🎉 Teams ingestion complete!")

    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
