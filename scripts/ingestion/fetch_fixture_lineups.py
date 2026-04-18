import time
import requests
from datetime import datetime, timezone
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, TimestampType, BooleanType

API_KEY = dbutils.secrets.get(scope="football", key="api_key")
API_BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
ENDPOINT = "fixtures/lineups"

spark = SparkSession.builder.getOrCreate()
requests_made = 0

LINEUP_SCHEMA = StructType([
    StructField("fixture_id", IntegerType(), True),
    StructField("team_id", IntegerType(), True),
    StructField("team_name", StringType(), True),
    StructField("formation", StringType(), True),
    StructField("coach_id", IntegerType(), True),
    StructField("coach_name", StringType(), True),
    StructField("ingested_at", TimestampType(), True),
])

LINEUP_PLAYER_SCHEMA = StructType([
    StructField("fixture_id", IntegerType(), True),
    StructField("team_id", IntegerType(), True),
    StructField("player_id", IntegerType(), True),
    StructField("player_name", StringType(), True),
    StructField("jersey_number", IntegerType(), True),
    StructField("position", StringType(), True),
    StructField("grid_position", StringType(), True),
    StructField("is_starter", BooleanType(), True),
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


def flatten_fixture_lineup(fixture_id: int, record: dict) -> dict:
    team = record.get("team", {})
    coach = record.get("coach", {})
    return {
        "fixture_id": fixture_id,
        "team_id": team.get("id"),
        "team_name": team.get("name"),
        "formation": record.get("formation"),
        "coach_id": coach.get("id"),
        "coach_name": coach.get("name"),
        "ingested_at": datetime.now(tz=timezone.utc),
    }


def flatten_lineup_player(
    fixture_id: int, team_id: int,
    player: dict, is_starter: bool
) -> dict:
    p = player.get("player", {})
    return {
        "fixture_id": fixture_id,
        "team_id": team_id,
        "player_id": p.get("id"),
        "player_name": p.get("name"),
        "jersey_number": p.get("number"),
        "position": p.get("pos"),
        "grid_position": p.get("grid"),
        "is_starter": is_starter,
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


def load_fixture_lineups(lineups: list) -> int:
    if not lineups:
        return 0
    existing_ids = {
        row[0] for row in spark.sql("""
            SELECT DISTINCT fixture_id
            FROM workspace.football_raw.raw_fixture_lineups
        """).collect()
    }
    new_lineups = [
        ln for ln in lineups
        if ln["fixture_id"] and ln["fixture_id"] not in existing_ids
    ]
    if not new_lineups:
        return 0
    df = spark.createDataFrame(new_lineups, schema=LINEUP_SCHEMA)
    df.write.mode("append").saveAsTable(
        "workspace.football_raw.raw_fixture_lineups"
    )
    return len(new_lineups)


def load_lineup_players(players: list) -> int:
    if not players:
        return 0
    existing_ids = {
        row[0] for row in spark.sql("""
            SELECT DISTINCT fixture_id
            FROM workspace.football_raw.raw_fixture_lineup_players
        """).collect()
    }
    new_players = [
        p for p in players
        if p["fixture_id"] and p["fixture_id"] not in existing_ids
    ]
    if not new_players:
        return 0
    df = spark.createDataFrame(new_players, schema=LINEUP_PLAYER_SCHEMA)
    df.write.mode("append").saveAsTable(
        "workspace.football_raw.raw_fixture_lineup_players"
    )
    return len(new_players)


def main():
    global requests_made
    print("📋 Fetching fixture lineups...")
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
            print(f"\n  Fetching lineups for league "
                  f"{league_id} season {season}...")
            fixture_ids = get_fixture_ids(league_id, season)
            print(f"  Found {len(fixture_ids)} fixtures")
            all_lineups = []
            all_players = []
            for fixture_id in fixture_ids:
                response = fetch_from_api(
                    "fixtures/lineups",
                    params={"fixture": fixture_id}
                )
                records = response.get("response", [])
                for record in records:
                    team_id = record.get("team", {}).get("id")
                    all_lineups.append(
                        flatten_fixture_lineup(fixture_id, record)
                    )
                    for player in record.get("startXI", []):
                        all_players.append(
                            flatten_lineup_player(
                                fixture_id, team_id, player, True
                            )
                        )
                    for player in record.get("substitutes", []):
                        all_players.append(
                            flatten_lineup_player(
                                fixture_id, team_id, player, False
                            )
                        )
            lineup_rows = load_fixture_lineups(all_lineups)
            player_rows = load_lineup_players(all_players)
            print(f"  ✅ Loaded {lineup_rows} lineups")
            print(f"  ✅ Loaded {player_rows} lineup players")
            update_metadata(
                f"{ENDPOINT}_{season}",
                lineup_rows + player_rows,
                "success", league_id
            )
        print("\n🎉 Fixture lineups ingestion complete!")
    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
