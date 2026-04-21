import time
import requests
from datetime import datetime, timezone
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, TimestampType

API_KEY = dbutils.secrets.get(scope="football", key="api_key")  # noqa: F821
API_BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
ENDPOINT = "fixtures/statistics"

spark = SparkSession.builder.getOrCreate()
requests_made = 0

FIXTURE_STATS_SCHEMA = StructType([
    StructField("fixture_id", IntegerType(), True),
    StructField("team_id", IntegerType(), True),
    StructField("team_name", StringType(), True),
    StructField("shots_on_goal", IntegerType(), True),
    StructField("shots_off_goal", IntegerType(), True),
    StructField("total_shots", IntegerType(), True),
    StructField("blocked_shots", IntegerType(), True),
    StructField("shots_inside_box", IntegerType(), True),
    StructField("shots_outside_box", IntegerType(), True),
    StructField("fouls", IntegerType(), True),
    StructField("corner_kicks", IntegerType(), True),
    StructField("offsides", IntegerType(), True),
    StructField("ball_possession", StringType(), True),
    StructField("yellow_cards", IntegerType(), True),
    StructField("red_cards", IntegerType(), True),
    StructField("goalkeeper_saves", IntegerType(), True),
    StructField("total_passes", IntegerType(), True),
    StructField("accurate_passes", IntegerType(), True),
    StructField("pass_accuracy", StringType(), True),
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
    try:
        result = spark.sql("""
            SELECT DISTINCT fixture_id
            FROM efua_data_platform.football_raw.raw_fixture_statistics
        """).collect()
        return {row[0] for row in result}
    except Exception:
        return set()


def flatten_fixture_statistics(
    fixture_id: int, record: dict
) -> dict:
    team = record.get("team", {})
    stats = {
        s.get("type"): s.get("value")
        for s in record.get("statistics", [])
    }
    return {
        "fixture_id": fixture_id,
        "team_id": team.get("id"),
        "team_name": team.get("name"),
        "shots_on_goal": stats.get("Shots on Goal"),
        "shots_off_goal": stats.get("Shots off Goal"),
        "total_shots": stats.get("Total Shots"),
        "blocked_shots": stats.get("Blocked Shots"),
        "shots_inside_box": stats.get("Shots insidebox"),
        "shots_outside_box": stats.get("Shots outsidebox"),
        "fouls": stats.get("Fouls"),
        "corner_kicks": stats.get("Corner Kicks"),
        "offsides": stats.get("Offsides"),
        "ball_possession": stats.get("Ball Possession"),
        "yellow_cards": stats.get("Yellow Cards"),
        "red_cards": stats.get("Red Cards"),
        "goalkeeper_saves": stats.get("Goalkeeper Saves"),
        "total_passes": stats.get("Total passes"),
        "accurate_passes": stats.get("Passes accurate"),
        "pass_accuracy": stats.get("Passes %"),
        "ingested_at": datetime.now(tz=timezone.utc),
    }


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


def load_fixture_statistics(statistics: list) -> int:
    if not statistics:
        return 0
    df = spark.createDataFrame(statistics, schema=FIXTURE_STATS_SCHEMA)
    df.write.mode("append").saveAsTable(
        "efua_data_platform.football_raw.raw_fixture_statistics"
    )
    return len(statistics)


def main():
    global requests_made
    print("📊 Fetching fixture statistics...")
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
            all_fixture_ids = get_fixture_ids(league_id, season)
            new_fixture_ids = [
                fid for fid in all_fixture_ids
                if fid not in ingested_fixture_ids
            ]
            if not new_fixture_ids:
                print(f"  League {league_id} season {season} "
                      f"— no new fixtures, skipping")
                continue
            print(f"\n  Fetching statistics for league {league_id} "
                  f"season {season}: {len(new_fixture_ids)} new fixture(s) "
                  f"(of {len(all_fixture_ids)} total)...")
            all_stats = []
            for fixture_id in new_fixture_ids:
                response = fetch_from_api(
                    "fixtures/statistics",
                    params={"fixture": fixture_id}
                )
                records = response.get("response", [])
                for record in records:
                    all_stats.append(
                        flatten_fixture_statistics(fixture_id, record)
                    )
            stat_rows = load_fixture_statistics(all_stats)
            ingested_fixture_ids.update(
                s["fixture_id"] for s in all_stats
            )
            print(f"  ✅ Loaded {stat_rows} fixture statistics")
            update_metadata(
                f"{ENDPOINT}_{season}",
                stat_rows, "success", league_id
            )
        print("\n🎉 Fixture statistics ingestion complete!")
    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
