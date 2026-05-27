import time
import threading
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    IntegerType,
    TimestampType,
)

API_KEY = dbutils.secrets.get(scope="football", key="api_key")  # noqa: F821

API_BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
ENDPOINT = "players/squads"

API_CONCURRENCY = 3
FLUSH_EVERY = 100

spark = SparkSession.builder.getOrCreate()

requests_made = 0
requests_lock = threading.Lock()
api_semaphore = threading.Semaphore(API_CONCURRENCY)


def is_transfer_window() -> bool:
    month = datetime.now().month
    return month in [1, 2, 6, 7, 8]


def get_team_ids() -> list:
    result = spark.sql("""
        SELECT DISTINCT team_id
        FROM efua_data_platform.football_raw.raw_teams
        ORDER BY team_id
    """).collect()
    return [row[0] for row in result]


def get_teams_to_skip(in_window: bool) -> set:
    """Teams recently fetched — one metadata query instead of per-team lookups."""
    threshold_days = 7 if in_window else 90
    result = spark.sql(f"""
        WITH latest_fetch AS (
            SELECT
                im.entity_id,
                im.last_ingested_at
            FROM efua_data_platform.football_raw.ingestion_metadata im
            INNER JOIN (
                SELECT entity_id, MAX(last_ingested_at) AS last_ingested_at
                FROM efua_data_platform.football_raw.ingestion_metadata
                WHERE endpoint = '{ENDPOINT}'
                AND status IN ('success', 'skipped')
                GROUP BY entity_id
            ) latest
                ON im.entity_id = latest.entity_id
                AND im.last_ingested_at = latest.last_ingested_at
                AND im.endpoint = '{ENDPOINT}'
        )
        SELECT entity_id
        FROM latest_fetch
        WHERE last_ingested_at >= CURRENT_TIMESTAMP - INTERVAL {threshold_days} DAYS
    """).collect()
    return {row[0] for row in result}


def get_existing_squad_combos() -> set:
    """Load dedupe keys once per run (not once per team)."""
    return {
        (row[0], row[1])
        for row in spark.sql("""
            SELECT team_id, player_id
            FROM efua_data_platform.football_raw.raw_team_squads
        """).collect()
    }


def fetch_from_api(endpoint: str, params: dict = {}) -> dict:
    global requests_made
    url = f"{API_BASE_URL}/{endpoint}"
    with api_semaphore:
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        with requests_lock:
            requests_made += 1
        remaining = response.headers.get("x-ratelimit-requests-remaining")
        limit = response.headers.get("x-ratelimit-requests-limit")
        print(f"  API requests remaining: {remaining}/{limit}")
        if remaining and int(remaining) < 100:
            raise Exception("⚠️ API request limit almost reached — stopping!")
        time.sleep(0.5)
    return response.json()


def flatten_squad_player(team_id: int, team_name: str, player: dict) -> dict:
    return {
        "team_id": team_id,
        "team_name": team_name,
        "player_id": player.get("id"),
        "player_name": player.get("name"),
        "player_age": player.get("age"),
        "jersey_number": player.get("number"),
        "position": player.get("position"),
        "photo_url": player.get("photo"),
        "ingested_at": datetime.now(tz=timezone.utc),
    }


def write_squad_players(players: list) -> None:
    if not players:
        return
    schema = StructType(
        [
            StructField("team_id", IntegerType(), True),
            StructField("team_name", StringType(), True),
            StructField("player_id", IntegerType(), True),
            StructField("player_name", StringType(), True),
            StructField("player_age", IntegerType(), True),
            StructField("jersey_number", IntegerType(), True),
            StructField("position", StringType(), True),
            StructField("photo_url", StringType(), True),
            StructField("ingested_at", TimestampType(), True),
        ]
    )
    df = spark.createDataFrame(players, schema=schema)
    df.write.mode("append").saveAsTable(
        "efua_data_platform.football_raw.raw_team_squads"
    )


def log_skipped_teams_bulk(team_ids: list) -> None:
    if not team_ids:
        return
    now = datetime.now(tz=timezone.utc)
    values = ", ".join(
        f"('{ENDPOINT}', {tid}, '{now.isoformat()}', 0, 0, 'skipped', '{now.isoformat()}')"
        for tid in team_ids
    )
    spark.sql(f"""
        INSERT INTO efua_data_platform.football_raw.ingestion_metadata
        (endpoint, entity_id, last_ingested_at, rows_inserted,
         requests_used, status, created_at)
        VALUES {values}
    """)


def log_success_teams_bulk(success_records: list) -> None:
    """success_records: list of (team_id, rows_inserted, started_at)"""
    if not success_records:
        return
    now = datetime.now(tz=timezone.utc)
    values = ", ".join(
        f"('{ENDPOINT}', {tid}, '{now.isoformat()}', {rows}, 1, "
        f"'success', '{now.isoformat()}', '{started.isoformat()}')"
        for tid, rows, started in success_records
    )
    spark.sql(f"""
        INSERT INTO efua_data_platform.football_raw.ingestion_metadata
        (endpoint, entity_id, last_ingested_at, rows_inserted,
         requests_used, status, created_at, started_at)
        VALUES {values}
    """)


def fetch_team(team_id: int) -> tuple:
    started_at = datetime.now(tz=timezone.utc)
    response = fetch_from_api(ENDPOINT, params={"team": team_id})
    records = response.get("response", [])
    return team_id, records, started_at


def flush(pending_players, success_records, skipped_to_log):
    write_squad_players(pending_players)
    log_success_teams_bulk(success_records)
    log_skipped_teams_bulk(skipped_to_log)
    pending_players.clear()
    success_records.clear()
    skipped_to_log.clear()


def main():
    print("👥 Fetching team squads...")

    team_ids = get_team_ids()
    in_window = is_transfer_window()
    teams_to_skip = get_teams_to_skip(in_window)
    existing_combos = get_existing_squad_combos()

    teams_to_fetch = [tid for tid in team_ids if tid not in teams_to_skip]
    skipped_recent_count = len(team_ids) - len(teams_to_fetch)

    print(f"  Found {len(team_ids)} teams")
    print(f"  Transfer window active: {in_window}")
    print(f"  Skipped (recently fetched): {skipped_recent_count}")
    print(f"  To fetch: {len(teams_to_fetch)}")

    pending_players = []
    success_records = []
    skipped_to_log = []
    combos_lock = threading.Lock()

    try:
        with ThreadPoolExecutor(max_workers=API_CONCURRENCY) as executor:
            futures = {executor.submit(fetch_team, tid): tid for tid in teams_to_fetch}
            completed = 0
            for future in as_completed(futures):
                team_id = futures[future]
                completed += 1
                try:
                    tid, records, started_at = future.result()

                    if not records:
                        skipped_to_log.append(tid)
                        print(f"  Team {tid}: no squad — skipped")
                        continue

                    all_players = []
                    for record in records:
                        team = record.get("team", {})
                        t_id = team.get("id")
                        t_name = team.get("name")
                        for player in record.get("players", []):
                            all_players.append(
                                flatten_squad_player(t_id, t_name, player)
                            )

                    with combos_lock:
                        new_players = [
                            p
                            for p in all_players
                            if (p["team_id"], p["player_id"]) not in existing_combos
                        ]
                        for p in new_players:
                            existing_combos.add((p["team_id"], p["player_id"]))

                    pending_players.extend(new_players)
                    success_records.append((tid, len(new_players), started_at))
                    print(
                        f"  Team {tid}: ✅ {len(new_players)} new squad players queued"
                    )

                except Exception as e:
                    print(f"  ⚠️ Team {team_id} failed: {e}")

                if completed % FLUSH_EVERY == 0:
                    flush(pending_players, success_records, skipped_to_log)
                    print(f"  Flushed at {completed}/{len(teams_to_fetch)} teams")

        flush(pending_players, success_records, skipped_to_log)
        print("\n🎉 Team squads ingestion complete!")

    except Exception as e:
        flush(pending_players, success_records, skipped_to_log)
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
