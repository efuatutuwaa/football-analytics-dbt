import time
import requests
from datetime import datetime, timezone
from pyspark.sql import SparkSession
from config import API_FOOTBALL_KEY as API_KEY
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, LongType, TimestampType, BooleanType

API_BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
ENDPOINT = "fixtures"

LEAGUE_IDS = [39, 2, 1, 4, 15, 140, 78, 61, 135]
SEASONS = list(range(2020, datetime.now().year + 1))

spark = SparkSession.builder.getOrCreate()
requests_made = 0

FIXTURE_SCHEMA = StructType([
    StructField("fixture_id", IntegerType(), True),
    StructField("referee", StringType(), True),
    StructField("timezone", StringType(), True),
    StructField("match_date", TimestampType(), True),
    StructField("match_timestamp", LongType(), True),
    StructField("first_period_start", LongType(), True),
    StructField("second_period_start", LongType(), True),
    StructField("venue_id", IntegerType(), True),
    StructField("venue_name", StringType(), True),
    StructField("venue_city", StringType(), True),
    StructField("status_long", StringType(), True),
    StructField("status_short", StringType(), True),
    StructField("elapsed_minutes", IntegerType(), True),
    StructField("extra_time", IntegerType(), True),
    StructField("league_id", IntegerType(), True),
    StructField("league_name", StringType(), True),
    StructField("league_country", StringType(), True),
    StructField("league_season", IntegerType(), True),
    StructField("league_round", StringType(), True),
    StructField("home_team_id", IntegerType(), True),
    StructField("home_team_name", StringType(), True),
    StructField("home_team_winner", BooleanType(), True),
    StructField("away_team_id", IntegerType(), True),
    StructField("away_team_name", StringType(), True),
    StructField("away_team_winner", BooleanType(), True),
    StructField("ingested_at", TimestampType(), True),
])

SCORE_SCHEMA = StructType([
    StructField("fixture_id", IntegerType(), True),
    StructField("halftime_home", IntegerType(), True),
    StructField("halftime_away", IntegerType(), True),
    StructField("fulltime_home", IntegerType(), True),
    StructField("fulltime_away", IntegerType(), True),
    StructField("extratime_home", IntegerType(), True),
    StructField("extratime_away", IntegerType(), True),
    StructField("penalty_home", IntegerType(), True),
    StructField("penalty_away", IntegerType(), True),
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


def _parse_ts(val: str):
    if not val:
        return None
    try:
        return datetime.fromisoformat(val)
    except (ValueError, TypeError):
        return None


def flatten_fixture(record: dict) -> dict:
    fixture = record.get("fixture", {})
    periods = fixture.get("periods", {})
    venue = fixture.get("venue", {})
    status = fixture.get("status", {})
    league = record.get("league", {})
    teams = record.get("teams", {})
    home = teams.get("home", {})
    away = teams.get("away", {})
    return {
        "fixture_id": fixture.get("id"),
        "referee": fixture.get("referee"),
        "timezone": fixture.get("timezone"),
        "match_date": _parse_ts(fixture.get("date")),
        "match_timestamp": fixture.get("timestamp"),
        "first_period_start": periods.get("first"),
        "second_period_start": periods.get("second"),
        "venue_id": venue.get("id"),
        "venue_name": venue.get("name"),
        "venue_city": venue.get("city"),
        "status_long": status.get("long"),
        "status_short": status.get("short"),
        "elapsed_minutes": status.get("elapsed"),
        "extra_time": status.get("extra"),
        "league_id": league.get("id"),
        "league_name": league.get("name"),
        "league_country": league.get("country"),
        "league_season": league.get("season"),
        "league_round": league.get("round"),
        "home_team_id": home.get("id"),
        "home_team_name": home.get("name"),
        "home_team_winner": home.get("winner"),
        "away_team_id": away.get("id"),
        "away_team_name": away.get("name"),
        "away_team_winner": away.get("winner"),
        "ingested_at": datetime.now(tz=timezone.utc),
    }


def flatten_fixture_score(fixture_id: int, record: dict) -> dict:
    score = record.get("score", {})
    halftime = score.get("halftime", {})
    fulltime = score.get("fulltime", {})
    extratime = score.get("extratime", {})
    penalty = score.get("penalty", {})
    return {
        "fixture_id": fixture_id,
        "halftime_home": halftime.get("home"),
        "halftime_away": halftime.get("away"),
        "fulltime_home": fulltime.get("home"),
        "fulltime_away": fulltime.get("away"),
        "extratime_home": extratime.get("home"),
        "extratime_away": extratime.get("away"),
        "penalty_home": penalty.get("home"),
        "penalty_away": penalty.get("away"),
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


def load_fixtures(fixtures: list) -> int:
    if not fixtures:
        return 0
    existing_ids = {
        row[0] for row in spark.sql("""
            SELECT fixture_id
            FROM workspace.football_raw.raw_fixtures
        """).collect()
    }
    new_fixtures = [
        f for f in fixtures
        if f["fixture_id"] and f["fixture_id"] not in existing_ids
    ]
    if not new_fixtures:
        return 0
    df = spark.createDataFrame(new_fixtures, schema=FIXTURE_SCHEMA)
    df.write.mode("append").saveAsTable(
        "workspace.football_raw.raw_fixtures"
    )
    return len(new_fixtures)


def load_fixture_scores(scores: list) -> int:
    if not scores:
        return 0
    existing_ids = {
        row[0] for row in spark.sql("""
            SELECT fixture_id
            FROM workspace.football_raw.raw_fixture_scores
        """).collect()
    }
    new_scores = [
        s for s in scores
        if s["fixture_id"] and s["fixture_id"] not in existing_ids
    ]
    if not new_scores:
        return 0
    df = spark.createDataFrame(new_scores, schema=SCORE_SCHEMA)
    df.write.mode("append").saveAsTable(
        "workspace.football_raw.raw_fixture_scores"
    )
    return len(new_scores)


def main():
    global requests_made
    print("🏟️ Fetching fixtures...")
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
                print(f"\n  Fetching fixtures for league "
                      f"{league_id} season {season}...")
                response = fetch_from_api(
                    ENDPOINT,
                    params={"league": league_id, "season": season}
                )
                records = response.get("response", [])
                if not records:
                    print("  No fixtures found — skipping")
                    continue
                fixtures = [flatten_fixture(r) for r in records]
                scores = [
                    flatten_fixture_score(
                        r.get("fixture", {}).get("id"), r
                    )
                    for r in records
                ]
                fixture_rows = load_fixtures(fixtures)
                score_rows = load_fixture_scores(scores)
                print(f"  ✅ Loaded {fixture_rows} fixtures")
                print(f"  ✅ Loaded {score_rows} scores")
                update_metadata(
                    f"{ENDPOINT}_{season}",
                    fixture_rows + score_rows,
                    "success", league_id
                )
        print("\n🎉 Fixtures ingestion complete!")
    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
