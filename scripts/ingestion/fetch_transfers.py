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
    DateType,
    TimestampType,
)

API_KEY = dbutils.secrets.get(scope="football", key="api_key")  # noqa: F821

API_BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
ENDPOINT = "transfers"

# Number of concurrent API requests — tune to your plan's req/min ceiling.
# 3 workers × (0.5s sleep + ~0.3s latency) ≈ 3x serial throughput while
# staying well within standard API-Football rate limits.
API_CONCURRENCY = 3

# Flush accumulated transfers to Delta every N players to bound memory
# usage and preserve progress on partial failures.
FLUSH_EVERY = 500

spark = SparkSession.builder.getOrCreate()

requests_made = 0
requests_lock = threading.Lock()
api_semaphore = threading.Semaphore(API_CONCURRENCY)


def is_transfer_window() -> bool:
    """Check if we are in a transfer window.
    Summer: June, July, August
    Winter: January, February
    Free agents can sign anytime — active players
    re-fetched monthly to catch these."""
    month = datetime.now().month
    return month in [1, 2, 6, 7, 8]


def get_players_to_fetch() -> list:
    """Return player IDs that have at least one match appearance (active).
    Merges the former get_player_ids + get_active_player_ids into one
    query, cutting inactive players before the main loop entirely."""
    result = spark.sql("""
        SELECT DISTINCT p.player_id
        FROM efua_data_platform.football_raw.raw_players p
        INNER JOIN efua_data_platform.football_raw.raw_player_statistics s
            ON p.player_id = s.player_id
        WHERE p.player_id IS NOT NULL
        ORDER BY p.player_id
    """).collect()
    return [row[0] for row in result]


def get_players_to_skip(in_window: bool) -> set:
    """Single SQL query to determine which players to skip based on
    re-fetch thresholds.

    Re-fetch strategy:
    - Active players with new transfers found on last fetch:
      7 days in window, 30 days outside
      ← catches free agents and emergency loans
    - Active players with no new transfers on last fetch (stable history):
      90 days in window, 180 days outside
      ← history is unlikely to change, avoid burning API quota
    - Inactive players:
      30 days in window, 90 days outside

    Returns set of player_ids to skip."""
    active_threshold = 7 if in_window else 30
    stable_threshold = 90 if in_window else 180
    inactive_threshold = 30 if in_window else 90
    result = spark.sql(f"""
        WITH latest_fetch AS (
            SELECT
                im.entity_id,
                im.last_ingested_at,
                im.rows_inserted,
                im.status
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
        ),
        recently_active AS (
            SELECT DISTINCT player_id
            FROM efua_data_platform.football_raw.raw_player_statistics
            WHERE ingested_at >= CURRENT_DATE - 30
        )
        SELECT lf.entity_id
        FROM latest_fetch lf
        LEFT JOIN recently_active ra ON lf.entity_id = ra.player_id
        WHERE (
            -- active player, new transfers found last time
            ra.player_id IS NOT NULL
            AND lf.rows_inserted > 0
            AND lf.last_ingested_at >= CURRENT_TIMESTAMP - INTERVAL {active_threshold} DAYS
        ) OR (
            -- active player, no new transfers last time (stable history)
            ra.player_id IS NOT NULL
            AND lf.rows_inserted = 0
            AND lf.status = 'success'
            AND lf.last_ingested_at >= CURRENT_TIMESTAMP - INTERVAL {stable_threshold} DAYS
        ) OR (
            -- inactive player
            ra.player_id IS NULL
            AND lf.last_ingested_at >= CURRENT_TIMESTAMP - INTERVAL {inactive_threshold} DAYS
        )
    """).collect()
    return {row[0] for row in result}


def fetch_from_api(endpoint: str, params: dict = {}) -> dict:
    """Fetch data from API-Football with rate limiting.
    Thread-safe: semaphore controls concurrency, lock protects counter."""
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


def _parse_date(val: str):
    """Parse date string to date object. Returns None on failure."""
    if not val:
        return None
    try:
        return datetime.strptime(val, "%Y-%m-%d").date()
    except Exception:
        return None


def _parse_ts(val: str):
    """Parse timestamp string to datetime object. Returns None on failure."""
    if not val:
        return None
    try:
        return datetime.fromisoformat(val)
    except Exception:
        return None


def flatten_transfer(
    player_id: int, player_name: str, last_updated: str, transfer: dict
) -> dict:
    """Flatten transfer record from API response."""
    teams = transfer.get("teams", {})
    team_in = teams.get("in", {})
    team_out = teams.get("out", {})
    return {
        "player_id": player_id,
        "player_name": player_name,
        "transfer_date": _parse_date(transfer.get("date")),
        "transfer_type": transfer.get("type"),
        "team_in_id": team_in.get("id"),
        "team_in_name": team_in.get("name"),
        "team_out_id": team_out.get("id"),
        "team_out_name": team_out.get("name"),
        "last_updated": _parse_ts(last_updated),
        "ingested_at": datetime.now(tz=timezone.utc),
    }


def update_metadata(
    endpoint: str,
    rows_inserted: int,
    status: str,
    entity_id: int = None,
    started_at: datetime = None,
):
    """Update ingestion metadata after each run."""
    now = datetime.now(tz=timezone.utc)
    entity_val = str(entity_id) if entity_id else "NULL"
    started_val = f"'{started_at.isoformat()}'" if started_at else "NULL"
    spark.sql(f"""
        INSERT INTO efua_data_platform.football_raw.ingestion_metadata
        (endpoint, entity_id, last_ingested_at, rows_inserted,
         requests_used, status, created_at, started_at)
        VALUES (
            '{endpoint}', {entity_val}, '{now.isoformat()}',
            {rows_inserted}, {requests_made}, '{status}',
            '{now.isoformat()}', {started_val}
        )
    """)


def get_existing_transfer_combos() -> set:
    """Load existing (player_id, transfer_date, team_in_id) combos from
    the last 24 months. Transfers older than that are already persisted
    and will never be re-inserted, so loading them into memory is waste."""
    return {
        (row[0], str(row[1]), row[2])
        for row in spark.sql("""
            SELECT player_id, transfer_date, team_in_id
            FROM efua_data_platform.football_raw.raw_transfers
            WHERE transfer_date IS NOT NULL
              AND transfer_date >= add_months(current_date(), -24)
        """).collect()
    }


def write_transfers(transfers: list) -> None:
    """Write pre-deduped transfers to raw_transfers in a single Spark job."""
    if not transfers:
        return
    schema = StructType(
        [
            StructField("player_id", IntegerType(), True),
            StructField("player_name", StringType(), True),
            StructField("transfer_date", DateType(), True),
            StructField("transfer_type", StringType(), True),
            StructField("team_in_id", IntegerType(), True),
            StructField("team_in_name", StringType(), True),
            StructField("team_out_id", IntegerType(), True),
            StructField("team_out_name", StringType(), True),
            StructField("last_updated", TimestampType(), True),
            StructField("ingested_at", TimestampType(), True),
        ]
    )
    df = spark.createDataFrame(transfers, schema=schema)
    df.write.mode("append").saveAsTable("efua_data_platform.football_raw.raw_transfers")


def log_skipped_players_bulk(player_ids: list):
    """Bulk insert skipped players into ingestion_metadata in one query
    instead of one INSERT per player."""
    if not player_ids:
        return
    now = datetime.now(tz=timezone.utc)
    values = ", ".join(
        f"('{ENDPOINT}', {pid}, '{now.isoformat()}', 0, 0, 'skipped', '{now.isoformat()}')"
        for pid in player_ids
    )
    spark.sql(f"""
        INSERT INTO efua_data_platform.football_raw.ingestion_metadata
        (endpoint, entity_id, last_ingested_at, rows_inserted,
         requests_used, status, created_at)
        VALUES {values}
    """)


def log_success_players_bulk(success_records: list):
    """Bulk insert successful fetches into ingestion_metadata.
    success_records: list of (player_id, rows_inserted, started_at)"""
    if not success_records:
        return
    now = datetime.now(tz=timezone.utc)
    values = ", ".join(
        f"('{ENDPOINT}', {pid}, '{now.isoformat()}', {rows}, 1, "
        f"'success', '{now.isoformat()}', '{started.isoformat()}')"
        for pid, rows, started in success_records
    )
    spark.sql(f"""
        INSERT INTO efua_data_platform.football_raw.ingestion_metadata
        (endpoint, entity_id, last_ingested_at, rows_inserted,
         requests_used, status, created_at, started_at)
        VALUES {values}
    """)


def fetch_player(player_id: int) -> tuple:
    """Fetch transfers for a single player. Returns (player_id, records, started_at).
    Designed to run inside a ThreadPoolExecutor worker."""
    started_at = datetime.now(tz=timezone.utc)
    response = fetch_from_api(ENDPOINT, params={"player": player_id})
    records = response.get("response", [])
    return player_id, records, started_at


def flush(pending_transfers, success_records, skipped_to_log):
    """Write pending transfers and metadata to Delta, then clear the lists."""
    write_transfers(pending_transfers)
    log_success_players_bulk(success_records)
    log_skipped_players_bulk(skipped_to_log)
    pending_transfers.clear()
    success_records.clear()
    skipped_to_log.clear()


def main():
    print("🔄 Fetching transfers...")

    player_ids = get_players_to_fetch()
    in_window = is_transfer_window()
    players_to_skip = get_players_to_skip(in_window)
    existing_combos = get_existing_transfer_combos()

    already_logged = {
        row[0]
        for row in spark.sql(f"""
            SELECT DISTINCT entity_id
            FROM efua_data_platform.football_raw.ingestion_metadata
            WHERE endpoint = '{ENDPOINT}'
            AND status = 'skipped'
        """).collect()
    }

    players_to_fetch = [pid for pid in player_ids if pid not in players_to_skip]
    skipped_recent_count = len(player_ids) - len(players_to_fetch)

    print(f"  Active players: {len(player_ids)}")
    print(f"  Transfer window active: {in_window}")
    print(f"  Skipped (recently fetched): {skipped_recent_count}")
    print(f"  To fetch: {len(players_to_fetch)}")

    skipped_to_log = []
    pending_transfers = []
    success_records = []
    combos_lock = threading.Lock()

    try:
        with ThreadPoolExecutor(max_workers=API_CONCURRENCY) as executor:
            futures = {
                executor.submit(fetch_player, pid): pid for pid in players_to_fetch
            }
            completed = 0
            for future in as_completed(futures):
                player_id = futures[future]
                completed += 1
                try:
                    pid, records, started_at = future.result()

                    if not records:
                        if pid not in already_logged:
                            skipped_to_log.append(pid)
                        continue

                    all_transfers = []
                    for record in records:
                        p_id = record.get("player", {}).get("id")
                        p_name = record.get("player", {}).get("name")
                        last_updated = record.get("update")
                        for transfer in record.get("transfers", []):
                            all_transfers.append(
                                flatten_transfer(p_id, p_name, last_updated, transfer)
                            )

                    with combos_lock:
                        new_transfers = [
                            t
                            for t in all_transfers
                            if (
                                t["player_id"],
                                str(t["transfer_date"]),
                                t["team_in_id"],
                            )
                            not in existing_combos
                        ]
                        for t in new_transfers:
                            existing_combos.add(
                                (
                                    t["player_id"],
                                    str(t["transfer_date"]),
                                    t["team_in_id"],
                                )
                            )

                    pending_transfers.extend(new_transfers)
                    success_records.append((pid, len(new_transfers), started_at))
                    print(
                        f"  Player {pid}: ✅ {len(new_transfers)} new transfers queued"
                    )

                except Exception as e:
                    print(f"  ⚠️ Player {player_id} failed: {e}")
                    skipped_to_log.append(player_id)

                # Flush every FLUSH_EVERY players to bound memory and preserve progress
                if completed % FLUSH_EVERY == 0:
                    flush(pending_transfers, success_records, skipped_to_log)
                    print(f"  Flushed at {completed}/{len(players_to_fetch)} players")

        # Final flush for remainder
        flush(pending_transfers, success_records, skipped_to_log)
        print("\n🎉 Transfers ingestion complete!")

    except Exception as e:
        flush(pending_transfers, success_records, skipped_to_log)
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
