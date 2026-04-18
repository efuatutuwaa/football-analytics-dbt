import time
import requests
from datetime import datetime, timezone
from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType, StructField, StringType,
    IntegerType, TimestampType
)

API_KEY = dbutils.secrets.get(scope="football", key="api_key")  # noqa: F821

API_BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
ENDPOINT = "players/squads"

spark = SparkSession.builder.getOrCreate()
requests_made = 0


# ── API Fetcher ───────────────────────────────────────────
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


# ── Get team IDs ──────────────────────────────────────────
def get_team_ids() -> list:
    result = spark.sql("""
        SELECT DISTINCT team_id
        FROM efua_data_platform.football_raw.raw_teams
        ORDER BY team_id
    """).collect()
    return [row[0] for row in result]


# ── Flatten squad player ──────────────────────────────────
def flatten_squad_player(
    team_id: int,
    team_name: str,
    player: dict
) -> dict:
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


# ── Incremental check ─────────────────────────────────────
def get_last_ingested_at(endpoint: str, entity_id: int = None):
    try:
        if entity_id:
            result = spark.sql(f"""
                SELECT last_ingested_at
                FROM efua_data_platform.football_raw.ingestion_metadata
                WHERE endpoint = '{endpoint}'
                AND entity_id = {entity_id}
                AND status IN ('success', 'skipped')
                ORDER BY last_ingested_at DESC
                LIMIT 1
            """).collect()
        else:
            result = spark.sql(f"""
                SELECT last_ingested_at
                FROM efua_data_platform.football_raw.ingestion_metadata
                WHERE endpoint = '{endpoint}'
                AND status IN ('success', 'skipped')
                ORDER BY last_ingested_at DESC
                LIMIT 1
            """).collect()
        return result[0][0] if result else None
    except Exception:
        return None


# ── Update metadata ───────────────────────────────────────
def update_metadata(
    endpoint: str,
    rows_inserted: int,
    status: str,
    entity_id: int = None
):
    now = datetime.now(tz=timezone.utc)
    entity_val = str(entity_id) if entity_id else "NULL"

    spark.sql(f"""
        INSERT INTO efua_data_platform.football_raw.ingestion_metadata
        (endpoint, entity_id, last_ingested_at, rows_inserted,
         requests_used, status, created_at)
        VALUES (
            '{endpoint}',
            {entity_val},
            '{now.isoformat()}',
            {rows_inserted},
            {requests_made},
            '{status}',
            '{now.isoformat()}'
        )
    """)


# ── Load squad players ────────────────────────────────────
def load_squad_players(players: list) -> int:
    if not players:
        return 0

    # fetch existing team IDs in squads table
    existing_ids = {
        row[0] for row in spark.sql("""
            SELECT DISTINCT team_id
            FROM efua_data_platform.football_raw.raw_team_squads
        """).collect()
    }

    new_players = [
        p for p in players
        if p["team_id"] and p["team_id"] not in existing_ids
    ]

    if not new_players:
        print("  No new squad players to load")
        return 0

    schema = StructType([
        StructField("team_id", IntegerType(), True),
        StructField("team_name", StringType(), True),
        StructField("player_id", IntegerType(), True),
        StructField("player_name", StringType(), True),
        StructField("player_age", IntegerType(), True),
        StructField("jersey_number", IntegerType(), True),
        StructField("position", StringType(), True),
        StructField("photo_url", StringType(), True),
        StructField("ingested_at", TimestampType(), True),
    ])

    df = spark.createDataFrame(new_players, schema=schema)
    df.write.mode("append").saveAsTable(
        "efua_data_platform.football_raw.raw_team_squads"
    )
    return len(new_players)


# ── Log skipped team ──────────────────────────────────────
def log_skipped_team(team_id: int):
    now = datetime.now(tz=timezone.utc)
    spark.sql(f"""
        INSERT INTO efua_data_platform.football_raw.ingestion_metadata
        (endpoint, entity_id, last_ingested_at, rows_inserted,
         requests_used, status, created_at)
        VALUES (
            '{ENDPOINT}',
            {team_id},
            '{now.isoformat()}',
            0,
            {requests_made},
            'skipped',
            '{now.isoformat()}'
        )
    """)


# ── Main ──────────────────────────────────────────────────
def main():
    global requests_made
    print("👥 Fetching team squads...")

    team_ids = get_team_ids()
    print(f"  Found {len(team_ids)} unique teams")

    try:
        for team_id in team_ids:
            requests_made = 0

            # ── incremental check before API call ──
            last_ingested_at = get_last_ingested_at(
                ENDPOINT, team_id
            )

            if last_ingested_at:
                print(f"  Team {team_id} already processed — skipping")
                continue

            response = fetch_from_api(
                ENDPOINT,
                params={"team": team_id}
            )
            records = response.get("response", [])

            if not records:
                print(
                    f"  No squad found for team {team_id} "
                    f"— logging as skipped"
                )
                log_skipped_team(team_id)
                continue

            all_players = []

            for record in records:
                team = record.get("team", {})
                tid = team.get("id")
                tname = team.get("name")

                for player in record.get("players", []):
                    all_players.append(
                        flatten_squad_player(tid, tname, player)
                    )

            squad_rows = load_squad_players(all_players)
            print(f"  Team {team_id}: ✅ {squad_rows} squad players")

            update_metadata(
                ENDPOINT,
                squad_rows,
                "success",
                team_id
            )

        print("\n🎉 Team squads ingestion complete!")

    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
