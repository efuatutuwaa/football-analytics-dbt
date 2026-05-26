import time
import requests
from datetime import datetime, timezone
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, TimestampType, BooleanType

API_KEY = dbutils.secrets.get(scope="football", key="api_key")  # noqa: F821
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
        FROM efua_data_platform.football_raw.raw_fixtures
        WHERE league_id = {league_id}
        AND league_season = {season}
        AND status_short = 'FT'
        ORDER BY fixture_id
    """).collect()
    return [row[0] for row in result]


def get_ingested_fixture_ids() -> set:
    """Return fixtures that have been successfully ingested OR
    marked as skipped because the API has no lineups for them
    (e.g. UCL qualifying rounds).
    """
    try:
        ingested = spark.sql("""
            SELECT DISTINCT fixture_id
            FROM efua_data_platform.football_raw.raw_fixture_lineups
        """).collect()
        skipped = spark.sql(f"""
            SELECT DISTINCT entity_id
            FROM efua_data_platform.football_raw.ingestion_metadata
            WHERE endpoint = '{ENDPOINT}'
            AND status = 'skipped'
        """).collect()
        return (
            {row[0] for row in ingested}
            | {row[0] for row in skipped if row[0] is not None}
        )
    except Exception:
        return set()


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


def update_metadata(
    endpoint: str, rows_inserted: int,
    status: str, entity_id: int = None,
    started_at: datetime = None
):
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


def load_fixture_lineups(lineups: list) -> int:
    if not lineups:
        return 0
    fixture_ids_str = ", ".join(
        str(fid) for fid in {ln["fixture_id"] for ln in lineups}
    )
    df = spark.createDataFrame(lineups, schema=LINEUP_SCHEMA)
    df = df.dropDuplicates(["fixture_id", "team_id"])
    df.cache()
    count = df.count()
    df.write.mode("overwrite").option(
        "replaceWhere", f"fixture_id IN ({fixture_ids_str})"
    ).saveAsTable("efua_data_platform.football_raw.raw_fixture_lineups")
    df.unpersist()
    return count


def load_lineup_players(players: list) -> int:
    if not players:
        return 0
    fixture_ids_str = ", ".join(
        str(fid) for fid in {p["fixture_id"] for p in players}
    )
    df = spark.createDataFrame(players, schema=LINEUP_PLAYER_SCHEMA)
    df = df.dropDuplicates(["fixture_id", "team_id", "player_id"])
    df.cache()
    count = df.count()
    df.write.mode("overwrite").option(
        "replaceWhere", f"fixture_id IN ({fixture_ids_str})"
    ).saveAsTable("efua_data_platform.football_raw.raw_fixture_lineup_players")
    df.unpersist()
    return count


def log_skipped_fixtures_bulk(fixture_ids: list):
    """Bulk insert fixtures with no API data into ingestion_metadata.
    Prevents re-querying these fixtures on every subsequent run
    (e.g. UCL qualifying rounds that API-Football does not cover).
    """
    if not fixture_ids:
        return
    now = datetime.now(tz=timezone.utc)
    values = ", ".join(
        f"('{ENDPOINT}', {fid}, '{now.isoformat()}', 0, 0, "
        f"'skipped', '{now.isoformat()}', NULL)"
        for fid in fixture_ids
    )
    spark.sql(f"""
        INSERT INTO efua_data_platform.football_raw.ingestion_metadata
        (endpoint, entity_id, last_ingested_at, rows_inserted,
         requests_used, status, created_at, started_at)
        VALUES {values}
    """)


def main():
    global requests_made
    print("📋 Fetching fixture lineups...")
    current_endpoint = None
    current_entity_id = None
    started_at = None
    try:
        ingested_fixture_ids = get_ingested_fixture_ids()
        print(f"  Already ingested fixture IDs: {len(ingested_fixture_ids)}")
        combos = spark.sql("""
            SELECT DISTINCT league_id, league_season
            FROM efua_data_platform.football_raw.raw_fixtures
            WHERE status_short = 'FT'
            ORDER BY league_id, league_season
        """).collect()
        for row in combos:
            league_id = row[0]
            season = row[1]
            requests_made = 0
            started_at = datetime.now(tz=timezone.utc)
            current_endpoint = f"{ENDPOINT}_{season}"
            current_entity_id = league_id
            all_fixture_ids = get_fixture_ids(league_id, season)
            new_fixture_ids = [
                fid for fid in all_fixture_ids
                if fid not in ingested_fixture_ids
            ]
            if not new_fixture_ids:
                print(f"  League {league_id} season {season} "
                      f"— no new fixtures, skipping")
                continue
            print(f"\n  Fetching lineups for league {league_id} "
                  f"season {season}: {len(new_fixture_ids)} new fixture(s) "
                  f"(of {len(all_fixture_ids)} total)...")
            all_lineups = []
            all_players = []
            skipped_fixtures = []
            for fixture_id in new_fixture_ids:
                response = fetch_from_api(
                    "fixtures/lineups",
                    params={"fixture": fixture_id}
                )
                records = response.get("response", [])
                if not records:
                    skipped_fixtures.append(fixture_id)
                    continue
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
            ingested_fixture_ids.update(
                ln["fixture_id"] for ln in all_lineups
            )
            print(f"  ✅ Loaded {lineup_rows} lineups")
            print(f"  ✅ Loaded {player_rows} lineup players")
            if skipped_fixtures:
                log_skipped_fixtures_bulk(skipped_fixtures)
                ingested_fixture_ids.update(skipped_fixtures)
                print(f"  ⏭️  Logged {len(skipped_fixtures)} fixtures "
                      f"with no API data (won't re-query)")
            update_metadata(
                f"{ENDPOINT}_{season}",
                lineup_rows + player_rows,
                "success", league_id,
                started_at=started_at
            )
        print("\n🎉 Fixture lineups ingestion complete!")
    except Exception as e:
        if current_endpoint:
            update_metadata(
                current_endpoint, 0, "failed",
                current_entity_id, started_at
            )
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
