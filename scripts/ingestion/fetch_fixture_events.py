import time
import requests
from datetime import datetime, timezone
from pyspark.sql import SparkSession
from config import API_FOOTBALL_KEY as API_KEY

API_BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
ENDPOINT = "fixtures/events"

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


def get_fixture_ids(league_id: int, season: int) -> list:
    result = spark.sql(f"""
        SELECT DISTINCT fixture_id
        FROM workspace.football_raw.raw_fixtures
        WHERE league_id = {league_id}
        AND league_season = {season}
        AND status_short = 'FT'
        ORDER BY fixture_id
    """).collect()
    return [row[0] for row in result]


def flatten_fixture_event(fixture_id: int, record: dict) -> dict:
    time_info = record.get("time", {})
    team = record.get("team", {})
    player = record.get("player", {})
    assist = record.get("assist", {})
    return {
        "fixture_id": fixture_id,
        "elapsed_minutes": time_info.get("elapsed"),
        "extra_minutes": time_info.get("extra"),
        "team_id": team.get("id"),
        "team_name": team.get("name"),
        "player_id": player.get("id"),
        "player_name": player.get("name"),
        "assist_player_id": assist.get("id"),
        "assist_player_name": assist.get("name"),
        "event_type": record.get("type"),
        "event_detail": record.get("detail"),
        "comments": record.get("comments"),
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


def load_fixture_events(events: list) -> int:
    if not events:
        return 0
    existing_ids = {
        row[0] for row in spark.sql("""
            SELECT DISTINCT fixture_id
            FROM workspace.football_raw.raw_fixture_events
        """).collect()
    }
    new_events = [
        e for e in events
        if e["fixture_id"] and e["fixture_id"] not in existing_ids
    ]
    if not new_events:
        return 0
    df = spark.createDataFrame(new_events)
    df.write.mode("append").saveAsTable(
        "workspace.football_raw.raw_fixture_events"
    )
    return len(new_events)


def main():
    global requests_made
    print("⚡ Fetching fixture events...")
    try:
        combos = spark.sql("""
            SELECT DISTINCT league_id, league_season
            FROM workspace.football_raw.raw_fixtures
            WHERE status_short = 'FT'
            ORDER BY league_id, league_season
        """).collect()
        for row in combos:
            league_id = row[0]
            season = row[1]
            requests_made = 0
            last_ingested_at = get_last_ingested_at(
                f"{ENDPOINT}_{season}", league_id
            )
            if last_ingested_at:
                print(f"  League {league_id} season {season} "
                      f"already ingested — skipping")
                continue
            print(f"\n  Fetching events for league "
                  f"{league_id} season {season}...")
            fixture_ids = get_fixture_ids(league_id, season)
            print(f"  Found {len(fixture_ids)} fixtures")
            all_events = []
            for fixture_id in fixture_ids:
                response = fetch_from_api(
                    "fixtures/events",
                    params={"fixture": fixture_id}
                )
                records = response.get("response", [])
                for record in records:
                    all_events.append(
                        flatten_fixture_event(fixture_id, record)
                    )
            event_rows = load_fixture_events(all_events)
            print(f"  ✅ Loaded {event_rows} fixture events")
            update_metadata(
                f"{ENDPOINT}_{season}",
                event_rows, "success", league_id
            )
        print("\n🎉 Fixture events ingestion complete!")
    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
