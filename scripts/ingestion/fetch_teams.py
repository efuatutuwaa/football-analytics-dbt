import os
import time
import requests
from datetime import datetime, timezone
from pyspark.sql import SparkSession

API_KEY = os.getenv("API_FOOTBALL_KEY")
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, TimestampType, BooleanType

API_BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
ENDPOINT = "teams"

LEAGUE_IDS = [39, 2, 1, 4, 15, 140, 78, 61, 135]
SEASONS = list(range(2020, datetime.now().year + 1))

spark = SparkSession.builder.getOrCreate()
requests_made = 0

TEAM_SCHEMA = StructType([
    StructField("team_id", IntegerType(), True),
    StructField("team_name", StringType(), True),
    StructField("team_code", StringType(), True),
    StructField("team_country", StringType(), True),
    StructField("founded_year", IntegerType(), True),
    StructField("is_national_team", BooleanType(), True),
    StructField("team_logo_url", StringType(), True),
    StructField("ingested_at", TimestampType(), True),
])

VENUE_SCHEMA = StructType([
    StructField("venue_id", IntegerType(), True),
    StructField("venue_name", StringType(), True),
    StructField("venue_address", StringType(), True),
    StructField("venue_city", StringType(), True),
    StructField("venue_capacity", IntegerType(), True),
    StructField("venue_surface", StringType(), True),
    StructField("venue_image_url", StringType(), True),
    StructField("ingested_at", TimestampType(), True),
])

TEAM_SEASON_SCHEMA = StructType([
    StructField("team_id", IntegerType(), True),
    StructField("league_id", IntegerType(), True),
    StructField("season_year", IntegerType(), True),
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


def flatten_team(record: dict) -> dict:
    team = record.get("team", {})
    return {
        "team_id": team.get("id"),
        "team_name": team.get("name"),
        "team_code": team.get("code"),
        "team_country": team.get("country"),
        "founded_year": team.get("founded"),
        "is_national_team": team.get("national"),
        "team_logo_url": team.get("logo"),
        "ingested_at": datetime.now(tz=timezone.utc),
    }


def flatten_venue(record: dict) -> dict:
    venue = record.get("venue", {})
    return {
        "venue_id": venue.get("id"),
        "venue_name": venue.get("name"),
        "venue_address": venue.get("address"),
        "venue_city": venue.get("city"),
        "venue_capacity": venue.get("capacity"),
        "venue_surface": venue.get("surface"),
        "venue_image_url": venue.get("image"),
        "ingested_at": datetime.now(tz=timezone.utc),
    }


def flatten_team_season(
    team_id: int, league_id: int, season: int
) -> dict:
    return {
        "team_id": team_id,
        "league_id": league_id,
        "season_year": season,
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


def load_teams(teams: list) -> int:
    if not teams:
        return 0
    existing_ids = {
        row[0] for row in spark.sql("""
            SELECT team_id FROM workspace.football_raw.raw_teams
        """).collect()
    }
    new_teams = [
        t for t in teams
        if t["team_id"] and t["team_id"] not in existing_ids
    ]
    if not new_teams:
        return 0
    df = spark.createDataFrame(new_teams, schema=TEAM_SCHEMA)
    df.write.mode("append").saveAsTable(
        "workspace.football_raw.raw_teams"
    )
    return len(new_teams)


def load_venues(venues: list) -> int:
    if not venues:
        return 0
    existing_ids = {
        row[0] for row in spark.sql("""
            SELECT venue_id FROM workspace.football_raw.raw_venues
        """).collect()
    }
    new_venues = [
        v for v in venues
        if v["venue_id"] and v["venue_id"] not in existing_ids
    ]
    if not new_venues:
        return 0
    df = spark.createDataFrame(new_venues, schema=VENUE_SCHEMA)
    df.write.mode("append").saveAsTable(
        "workspace.football_raw.raw_venues"
    )
    return len(new_venues)


def load_team_seasons(team_seasons: list) -> int:
    if not team_seasons:
        return 0
    existing_combos = {
        (row[0], row[1], row[2]) for row in spark.sql("""
            SELECT team_id, league_id, season_year
            FROM workspace.football_raw.raw_team_seasons
        """).collect()
    }
    new_seasons = [
        s for s in team_seasons
        if (s["team_id"], s["league_id"], s["season_year"])
        not in existing_combos
    ]
    if not new_seasons:
        return 0
    df = spark.createDataFrame(new_seasons, schema=TEAM_SEASON_SCHEMA)
    df.write.mode("append").saveAsTable(
        "workspace.football_raw.raw_team_seasons"
    )
    return len(new_seasons)


def main():
    global requests_made
    print("⚽ Fetching teams...")
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
                print(f"\n  Fetching teams for league "
                      f"{league_id} season {season}...")
                response = fetch_from_api(
                    ENDPOINT,
                    params={"league": league_id, "season": season}
                )
                records = response.get("response", [])
                if not records:
                    print("  No teams found — skipping")
                    continue
                teams = [flatten_team(r) for r in records]
                venues = [flatten_venue(r) for r in records]
                team_seasons = [
                    flatten_team_season(
                        r.get("team", {}).get("id"), league_id, season
                    )
                    for r in records
                ]
                team_rows = load_teams(teams)
                venue_rows = load_venues(venues)
                season_rows = load_team_seasons(team_seasons)
                print(f"  ✅ Loaded {team_rows} new teams")
                print(f"  ✅ Loaded {venue_rows} new venues")
                print(f"  ✅ Loaded {season_rows} team season records")
                update_metadata(
                    f"{ENDPOINT}_{season}",
                    team_rows + venue_rows + season_rows,
                    "success", league_id
                )
        print("\n🎉 Teams ingestion complete!")
    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
