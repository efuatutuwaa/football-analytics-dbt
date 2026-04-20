import time
import requests
from datetime import datetime, timezone
from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType, StructField, StringType,
    IntegerType, DateType, TimestampType
)

API_KEY = dbutils.secrets.get(scope="football", key="api_key")  # noqa: F821

API_BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
ENDPOINT = "transfers"

spark = SparkSession.builder.getOrCreate()
requests_made = 0


def is_transfer_window() -> bool:
    month = datetime.now().month
    return month in [1, 2, 6, 7, 8]


def get_active_player_ids() -> set:
    result = spark.sql("""
        SELECT DISTINCT player_id
        FROM efua_data_platform.football_raw.raw_player_statistics
        WHERE player_id IS NOT NULL
    """).collect()
    return {row[0] for row in result}


def get_players_to_skip(in_window: bool) -> set:
    active_threshold = 7 if in_window else 30
    inactive_threshold = 30 if in_window else 90
    result = spark.sql(f"""
        WITH latest_ingestion AS (
            SELECT entity_id, MAX(last_ingested_at) AS last_ingested_at
            FROM efua_data_platform.football_raw.ingestion_metadata
            WHERE endpoint = '{ENDPOINT}'
            AND status IN ('success', 'skipped')
            GROUP BY entity_id
        ),
        recently_active AS (
            SELECT DISTINCT player_id
            FROM efua_data_platform.football_raw.raw_player_statistics
            WHERE ingested_at >= CURRENT_DATE - 30
        )
        SELECT li.entity_id
        FROM latest_ingestion li
        LEFT JOIN recently_active ra ON li.entity_id = ra.player_id
        WHERE (
            ra.player_id IS NOT NULL
            AND li.last_ingested_at >= CURRENT_TIMESTAMP - INTERVAL {active_threshold} DAYS
        ) OR (
            ra.player_id IS NULL
            AND li.last_ingested_at >= CURRENT_TIMESTAMP - INTERVAL {inactive_threshold} DAYS
        )
    """).collect()
    return {row[0] for row in result}


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


def get_player_ids() -> list:
    result = spark.sql("""
        SELECT DISTINCT player_id
        FROM efua_data_platform.football_raw.raw_players
        ORDER BY player_id
    """).collect()
    return [row[0] for row in result]


def _parse_date(val: str):
    if not val:
        return None
    try:
        return datetime.strptime(val, "%Y-%m-%d").date()
    except Exception:
        return None


def _parse_ts(val: str):
    if not val:
        return None
    try:
        return datetime.fromisoformat(val)
    except Exception:
        return None


def flatten_transfer(
    player_id: int,
    player_name: str,
    last_updated: str,
    transfer: dict
) -> dict:
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


def get_last_ingested_at(endpoint: str, entity_id: int = None):
    try:
        if entity_id:
            result = spark.sql(f"""
                SELECT last_ingested_at
                FROM efua_data_platform.football_raw.ingestion_metadata
                WHERE endpoint = '{endpoint}'
                AND entity_id = {entity_id}
                AND status IN ('success', 'skipped')
                ORDER BY last_ingested_at DESC LIMIT 1
            """).collect()
        else:
            result = spark.sql(f"""
                SELECT last_ingested_at
                FROM efua_data_platform.football_raw.ingestion_metadata
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
        INSERT INTO efua_data_platform.football_raw.ingestion_metadata
        (endpoint, entity_id, last_ingested_at, rows_inserted,
         requests_used, status, created_at)
        VALUES (
            '{endpoint}', {entity_val}, '{now.isoformat()}',
            {rows_inserted}, {requests_made}, '{status}',
            '{now.isoformat()}'
        )
    """)


def load_transfers(transfers: list) -> int:
    if not transfers:
        return 0
    existing_combos = {
        (row[0], str(row[1]), row[2])
        for row in spark.sql("""
            SELECT player_id, transfer_date, team_in_id
            FROM efua_data_platform.football_raw.raw_transfers
            WHERE transfer_date IS NOT NULL
        """).collect()
    }
    new_transfers = [
        t for t in transfers
        if (t["player_id"], str(t["transfer_date"]), t["team_in_id"])
        not in existing_combos
    ]
    if not new_transfers:
        return 0
    schema = StructType([
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
    ])
    df = spark.createDataFrame(new_transfers, schema=schema)
    df.write.mode("append").saveAsTable(
        "efua_data_platform.football_raw.raw_transfers"
    )
    return len(new_transfers)


def log_skipped_player(player_id: int):
    now = datetime.now(tz=timezone.utc)
    spark.sql(f"""
        INSERT INTO efua_data_platform.football_raw.ingestion_metadata
        (endpoint, entity_id, last_ingested_at, rows_inserted,
         requests_used, status, created_at)
        VALUES (
            '{ENDPOINT}', {player_id}, '{now.isoformat()}',
            0, {requests_made}, 'skipped', '{now.isoformat()}'
        )
    """)


def main():
    global requests_made
    print("🔄 Fetching transfers...")

    player_ids = get_player_ids()
    active_ids = get_active_player_ids()
    in_window = is_transfer_window()
    players_to_skip = get_players_to_skip(in_window)

    print(f"  Total players: {len(player_ids)}")
    print(f"  Active players: {len(active_ids)}")
    print(f"  Transfer window active: {in_window}")
    print(f"  Players to skip (recently fetched): {len(players_to_skip)}")

    try:
        for player_id in player_ids:
            requests_made = 0

            if player_id not in active_ids:
                log_skipped_player(player_id)
                continue

            if player_id in players_to_skip:
                print(f"  Player {player_id} recently checked — skipping")
                continue

            response = fetch_from_api(
                ENDPOINT,
                params={"player": player_id}
            )
            records = response.get("response", [])

            if not records:
                print(
                    f"  No transfers for player {player_id} "
                    f"— logging as skipped"
                )
                log_skipped_player(player_id)
                continue

            all_transfers = []
            for record in records:
                pid = record.get("player", {}).get("id")
                pname = record.get("player", {}).get("name")
                last_updated = record.get("update")
                for transfer in record.get("transfers", []):
                    all_transfers.append(
                        flatten_transfer(pid, pname, last_updated, transfer)
                    )

            transfer_rows = load_transfers(all_transfers)
            print(f"  Player {player_id}: ✅ {transfer_rows} transfers")

            update_metadata(
                ENDPOINT, transfer_rows,
                "success", player_id
            )

        print("\n🎉 Transfers ingestion complete!")

    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
