import time
import requests
from datetime import datetime, timezone, date
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, TimestampType, BooleanType, DateType

API_KEY = dbutils.secrets.get(scope="football", key="api_key")  # noqa: F821
API_BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
ENDPOINT = "leagues"

LEAGUE_IDS = [39, 2, 1, 4, 15, 140, 78, 61, 135]
SEASONS = list(range(2020, datetime.now().year + 1))

spark = SparkSession.builder.getOrCreate()
requests_made = 0

LEAGUE_SCHEMA = StructType([
    StructField("league_id", IntegerType(), True),
    StructField("league_name", StringType(), True),
    StructField("league_type", StringType(), True),
    StructField("league_logo_url", StringType(), True),
    StructField("country_name", StringType(), True),
    StructField("country_code", StringType(), True),
    StructField("country_flag_url", StringType(), True),
    StructField("ingested_at", TimestampType(), True),
])

LEAGUE_SEASON_SCHEMA = StructType([
    StructField("league_id", IntegerType(), True),
    StructField("season_year", IntegerType(), True),
    StructField("season_start", DateType(), True),
    StructField("season_end", DateType(), True),
    StructField("is_current_season", BooleanType(), True),
    StructField("coverage_fixtures_events", BooleanType(), True),
    StructField("coverage_fixtures_lineups", BooleanType(), True),
    StructField("coverage_standings", BooleanType(), True),
    StructField("coverage_players", BooleanType(), True),
    StructField("coverage_top_scorers", BooleanType(), True),
    StructField("coverage_injuries", BooleanType(), True),
    StructField("coverage_predictions", BooleanType(), True),
    StructField("coverage_odds", BooleanType(), True),
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


def _parse_date(val: str):
    if not val:
        return None
    try:
        return date.fromisoformat(val)
    except (ValueError, TypeError):
        return None


def flatten_league(record: dict) -> dict:
    league = record.get("league", {})
    country = record.get("country", {})
    return {
        "league_id": league.get("id"),
        "league_name": league.get("name"),
        "league_type": league.get("type"),
        "league_logo_url": league.get("logo"),
        "country_name": country.get("name"),
        "country_code": country.get("code"),
        "country_flag_url": country.get("flag"),
        "ingested_at": datetime.now(tz=timezone.utc),
    }


def flatten_league_season(league_id: int, season: dict) -> dict:
    coverage = season.get("coverage", {})
    fixtures = coverage.get("fixtures", {})
    return {
        "league_id": league_id,
        "season_year": season.get("year"),
        "season_start": _parse_date(season.get("start")),
        "season_end": _parse_date(season.get("end")),
        "is_current_season": season.get("current"),
        "coverage_fixtures_events": fixtures.get("events"),
        "coverage_fixtures_lineups": fixtures.get("lineups"),
        "coverage_standings": coverage.get("standings"),
        "coverage_players": coverage.get("players"),
        "coverage_top_scorers": coverage.get("top_scorers"),
        "coverage_injuries": coverage.get("injuries"),
        "coverage_predictions": coverage.get("predictions"),
        "coverage_odds": coverage.get("odds"),
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


def should_refetch_league(league_id: int) -> bool:
    last_ingested = get_last_ingested_at(ENDPOINT, league_id)
    if not last_ingested:
        return True
    days_since = (
        datetime.now(tz=timezone.utc)
        - last_ingested.replace(tzinfo=timezone.utc)
    ).days
    return days_since >= 365


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


def load_leagues(leagues: list) -> int:
    if not leagues:
        return 0
    existing_ids = {
        row[0] for row in spark.sql("""
            SELECT league_id FROM efua_data_platform.football_raw.raw_leagues
        """).collect()
    }
    new_leagues = [
        lg for lg in leagues
        if lg["league_id"] and lg["league_id"] not in existing_ids
    ]
    if not new_leagues:
        return 0
    df = spark.createDataFrame(new_leagues, schema=LEAGUE_SCHEMA)
    df.write.mode("append").saveAsTable(
        "efua_data_platform.football_raw.raw_leagues"
    )
    return len(new_leagues)


def load_league_seasons(seasons: list) -> int:
    if not seasons:
        return 0
    existing_combos = {
        (row[0], row[1]) for row in spark.sql("""
            SELECT league_id, season_year
            FROM efua_data_platform.football_raw.raw_league_seasons
        """).collect()
    }
    new_seasons = [
        s for s in seasons
        if (s["league_id"], s["season_year"]) not in existing_combos
    ]
    if not new_seasons:
        return 0
    df = spark.createDataFrame(new_seasons, schema=LEAGUE_SEASON_SCHEMA)
    df.write.mode("append").saveAsTable(
        "efua_data_platform.football_raw.raw_league_seasons"
    )
    return len(new_seasons)


def main():
    global requests_made
    print("🏆 Fetching leagues...")
    try:
        for league_id in LEAGUE_IDS:
            requests_made = 0
            if not should_refetch_league(league_id):
                print(f"  League {league_id} recently fetched — skipping")
                continue
            print(f"\n  Fetching league {league_id}...")
            response = fetch_from_api(ENDPOINT, params={"id": league_id})
            records = response.get("response", [])
            leagues = []
            seasons = []
            for record in records:
                leagues.append(flatten_league(record))
                lid = record.get("league", {}).get("id")
                for season in record.get("seasons", []):
                    if season.get("year") in SEASONS:
                        seasons.append(flatten_league_season(lid, season))
            league_rows = load_leagues(leagues)
            season_rows = load_league_seasons(seasons)
            print(f"  ✅ Loaded {league_rows} leagues")
            print(f"  ✅ Loaded {season_rows} seasons")
            update_metadata(ENDPOINT, league_rows + season_rows, "success", league_id)
        print("\n🎉 Leagues ingestion complete!")
    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
