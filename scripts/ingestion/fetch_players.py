import os
import time
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
from pyspark.sql import SparkSession

load_dotenv()

API_KEY = os.getenv("API_FOOTBALL_KEY")

if not API_KEY:
    raise ValueError("Missing API_FOOTBALL_KEY — check your .env file")

API_BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
ENDPOINT = "players"

LEAGUE_IDS = [39, 2, 1, 4, 15, 140, 78, 61, 135]
SEASONS = [2020, 2021, 2022, 2023, 2024, 2025]

spark = SparkSession.builder.getOrCreate()
requests_made = 0


def fetch_from_api(endpoint: str, params: dict = {}) -> dict:
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


def fetch_all_pages(league_id: int, season: int) -> list:
    all_records = []
    page = 1
    while True:
        print(f"    Fetching page {page}...")
        response = fetch_from_api(
            ENDPOINT,
            params={"league": league_id, "season": season, "page": page}
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


def flatten_player(record: dict) -> dict:
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


def get_last_ingested_at(endpoint: str, entity_id: int = None):
    try:
        if entity_id:
            result = spark.sql(f"""
                SELECT last_ingested_at
                FROM workspace.football_raw.ingestion_metadata
                WHERE endpoint = '{endpoint}'
                AND entity_id = {entity_id}
                AND status IN ('success', 'skipped')
                ORDER BY last_ingested_at DESC LIMIT 1
            """).collect()
        else:
            result = spark.sql(f"""
                SELECT last_ingested_at
                FROM workspace.football_raw.ingestion_metadata
                WHERE endpoint = '{endpoint}'
                AND status IN ('success', 'skipped')
                ORDER BY last_ingested_at DESC LIMIT 1
            """).collect()
        return result[0][0] if result else None
    except Exception:
        return None


def update_metadata(
    endpoint: str, rows_inserted: int,
    status: str, entity_id: int = None
):
    now = datetime.now(tz=timezone.utc)
    entity_val = str(entity_id) if entity_id else "NULL"
    spark.sql(f"""
        INSERT INTO workspace.football_raw.ingestion_metadata
        (endpoint, entity_id, last_ingested_at, rows_inserted,
         requests_used, status, created_at)
        VALUES (
            '{endpoint}', {entity_val}, '{now.isoformat()}',
            {rows_inserted}, {requests_made}, '{status}',
            '{now.isoformat()}'
        )
    """)


def load_players(players: list) -> int:
    if not players:
        return 0
    existing_ids = {
        row[0] for row in spark.sql("""
            SELECT player_id FROM workspace.football_raw.raw_players
        """).collect()
    }
    new_players = [
        p for p in players
        if p["player_id"] and p["player_id"] not in existing_ids
    ]
    if not new_players:
        print("  No new players to load")
        return 0
    df = spark.createDataFrame(new_players)
    df.write.mode("append").saveAsTable(
        "workspace.football_raw.raw_players"
    )
    return len(new_players)


def main():
    global requests_made
    print("👤 Fetching players...")
    try:
        for league_id in LEAGUE_IDS:
            for season in SEASONS:
                requests_made = 0
                last_ingested_at = get_last_ingested_at(
                    f"{ENDPOINT}_{season}", league_id
                )
                if last_ingested_at:
                    print(f"  League {league_id} season {season} "
                          f"already ingested — skipping")
                    continue
                print(f"\n  Fetching players for league "
                      f"{league_id} season {season}...")
                records = fetch_all_pages(league_id, season)
                if not records:
                    print(f"  No players found — skipping")
                    continue
                players = [flatten_player(r) for r in records]
                print(f"  Got {len(players)} players")
                player_rows = load_players(players)
                print(f"  ✅ Loaded {player_rows} new players")
                update_metadata(
                    f"{ENDPOINT}_{season}",
                    player_rows, "success", league_id
                )
        print("\n🎉 Players ingestion complete!")
    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
