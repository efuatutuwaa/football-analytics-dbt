import time
import requests
from datetime import datetime, timezone, date
from pyspark.sql import SparkSession
from config import API_FOOTBALL_KEY as API_KEY
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, TimestampType, DateType

API_BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
ENDPOINT = "transfers"

spark = SparkSession.builder.getOrCreate()
requests_made = 0

TRANSFER_SCHEMA = StructType([
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
        FROM workspace.football_raw.raw_players
        ORDER BY player_id
    """).collect()
    return [row[0] for row in result]


def _parse_date(val: str):
    if not val:
        return None
    try:
        return date.fromisoformat(val)
    except (ValueError, TypeError):
        return None


def _parse_ts(val: str):
    if not val:
        return None
    try:
        return datetime.fromisoformat(val)
    except (ValueError, TypeError):
        return None


def flatten_transfer(
    player_id: int, player_name: str,
    last_updated: str, transfer: dict
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


def load_transfers(transfers: list) -> int:
    if not transfers:
        return 0
    existing_ids = {
        row[0] for row in spark.sql("""
            SELECT DISTINCT player_id
            FROM workspace.football_raw.raw_transfers
        """).collect()
    }
    new_transfers = [
        t for t in transfers
        if t["player_id"] and t["player_id"] not in existing_ids
    ]
    if not new_transfers:
        return 0
    df = spark.createDataFrame(new_transfers, schema=TRANSFER_SCHEMA)
    df.write.mode("append").saveAsTable(
        "workspace.football_raw.raw_transfers"
    )
    return len(new_transfers)


def log_skipped_player(player_id: int):
    now = datetime.now(tz=timezone.utc)
    spark.sql(f"""
        INSERT INTO workspace.football_raw.ingestion_metadata
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
    try:
        player_ids = get_player_ids()
        print(f"  Found {len(player_ids)} players")
        for player_id in player_ids:
            requests_made = 0
            last_ingested_at = get_last_ingested_at(ENDPOINT, player_id)
            if last_ingested_at:
                print(f"  Player {player_id} already processed — skipping")
                continue
            response = fetch_from_api(
                ENDPOINT, params={"player": player_id}
            )
            records = response.get("response", [])
            if not records:
                print(f"  No transfers for player {player_id} — skipping")
                log_skipped_player(player_id)
                continue
            all_transfers = []
            for record in records:
                pid = record.get("player", {}).get("id")
                pname = record.get("player", {}).get("name")
                last_updated = record.get("update")
                for transfer in record.get("transfers", []):
                    all_transfers.append(
                        flatten_transfer(
                            pid, pname, last_updated, transfer
                        )
                    )
            transfer_rows = load_transfers(all_transfers)
            print(f"  Player {player_id}: ✅ {transfer_rows} transfers")
            update_metadata(
                ENDPOINT, transfer_rows, "success", player_id
            )
        print("\n🎉 Transfers ingestion complete!")
    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
