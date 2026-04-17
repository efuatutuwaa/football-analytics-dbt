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
ENDPOINT = "players"

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


# ── Fetch all pages ───────────────────────────────────────
def fetch_all_pages(league_id: int, season: int) -> list:
    """Fetch all pages of players for a league and season."""
    all_records = []
    page = 1

    while True:
        print(f"    Fetching page {page}...")
        response = fetch_from_api(
            ENDPOINT,
            params={
                "league": league_id,
                "season": season,
                "page": page
            }
        )

        records = response.get("response", [])
        if not records:
            break

        all_records.extend(records)

        paging = response.get("paging", {})
        current = paging.get("current", 1)
        total = paging.get("total", 1)

        print(f"    Page {current}/{total} — {len(records)} players")

        if current >= total:
            break

        page += 1

    return all_records


# ── Flatten player ────────────────────────────────────────
def flatten_player(record: dict) -> dict:
    """Flatten player bio from API response."""
    player = record.get("player", {})
    birth = player.get("birth", {})

    return {
        "player_id": player.get("id"),
        "player_name": player.get("name"),
        "firstname": player.get("firstname"),
        "lastname": player.get("lastname"),
        "age": player.get("age"),
        "birth_date": birth.get("date"),
        "birth_place": birth.get("place"),
        "birth_country": birth.get("country"),
        "nationality": player.get("nationality"),
        "height": player.get("height"),
        "weight": player.get("weight"),
        "photo_url": player.get("photo"),
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


# ── Load players ──────────────────────────────────────────
def load_players(cursor, players: list) -> int:
    """Load unique player bio into football_raw.raw_players."""

    # fetch existing player IDs once
    cursor.execute("SELECT player_id FROM football_raw.raw_players")
    existing_ids = {row[0] for row in cursor.fetchall()}

    # filter out already existing players
    new_players = [
        p for p in players
        if p["player_id"] and p["player_id"] not in existing_ids
    ]

    if not new_players:
        print("  No new players to load")
        return 0

    # batch insert all new players
    cursor.executemany("""
        INSERT INTO football_raw.raw_players (
            player_id,
            player_name,
            firstname,
            lastname,
            age,
            birth_date,
            birth_place,
            birth_country,
            nationality,
            height,
            weight,
            photo_url,
            ingested_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        [
            p["player_id"],
            p["player_name"],
            p["firstname"],
            p["lastname"],
            p["age"],
            p["birth_date"],
            p["birth_place"],
            p["birth_country"],
            p["nationality"],
            p["height"],
            p["weight"],
            p["photo_url"],
            p["ingested_at"],
        ]
        for p in new_players
    ])

    return len(new_players)


# ── Main loader ───────────────────────────────────────────
def load_to_databricks(
    league_id: int,
    season: int,
    players: list
) -> None:
    """Load players into Databricks."""
    with sql.connect(
        server_hostname=DATABRICKS_HOST,
        http_path=DATABRICKS_HTTP_PATH,
        access_token=DATABRICKS_TOKEN,
        catalog="workspace"
    ) as connection:
        with connection.cursor() as cursor:

            player_rows = load_players(cursor, players)
            print(f"  ✅ Loaded {player_rows} new players")

            update_metadata(
                cursor,
                f"{ENDPOINT}_{season}",
                player_rows,
                "success",
                league_id
            )


# ── Main ──────────────────────────────────────────────────
def main():
    global requests_made
    print("👤 Fetching players...")

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

                print(f"\n  Fetching players for league "
                      f"{league_id} season {season}...")

                records = fetch_all_pages(league_id, season)

                if not records:
                    print(f"  No players found for league {league_id} "
                          f"season {season} — skipping")
                    continue

                players = [flatten_player(r) for r in records]
                print(f"  Got {len(players)} players")

                load_to_databricks(league_id, season, players)

        print("\n🎉 Players ingestion complete!")

    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
