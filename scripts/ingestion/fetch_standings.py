import os
import time
import requests
from datetime import datetime, timezone
from pyspark.sql import SparkSession

from pyspark.sql.types import StructType, StructField, StringType, IntegerType, TimestampType

API_KEY = os.getenv("API_FOOTBALL_KEY")
API_BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
ENDPOINT = "standings"

LEAGUE_IDS = [39, 2, 1, 4, 15, 140, 78, 61, 135]
SEASONS = list(range(2020, datetime.now().year + 1))

spark = SparkSession.builder.getOrCreate()
requests_made = 0

STANDING_SCHEMA = StructType([
    StructField("league_id", IntegerType(), True),
    StructField("league_name", StringType(), True),
    StructField("league_season", IntegerType(), True),
    StructField("team_id", IntegerType(), True),
    StructField("team_name", StringType(), True),
    StructField("rank", IntegerType(), True),
    StructField("points", IntegerType(), True),
    StructField("goals_diff", IntegerType(), True),
    StructField("group_name", StringType(), True),
    StructField("form", StringType(), True),
    StructField("status", StringType(), True),
    StructField("description", StringType(), True),
    StructField("all_played", IntegerType(), True),
    StructField("all_wins", IntegerType(), True),
    StructField("all_draws", IntegerType(), True),
    StructField("all_losses", IntegerType(), True),
    StructField("all_goals_for", IntegerType(), True),
    StructField("all_goals_against", IntegerType(), True),
    StructField("home_played", IntegerType(), True),
    StructField("home_wins", IntegerType(), True),
    StructField("home_draws", IntegerType(), True),
    StructField("home_losses", IntegerType(), True),
    StructField("home_goals_for", IntegerType(), True),
    StructField("home_goals_against", IntegerType(), True),
    StructField("away_played", IntegerType(), True),
    StructField("away_wins", IntegerType(), True),
    StructField("away_draws", IntegerType(), True),
    StructField("away_losses", IntegerType(), True),
    StructField("away_goals_for", IntegerType(), True),
    StructField("away_goals_against", IntegerType(), True),
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


def _parse_ts(val: str):
    if not val:
        return None
    try:
        return datetime.fromisoformat(val)
    except (ValueError, TypeError):
        return None


def flatten_standing(
    league_id: int, league_name: str,
    season: int, record: dict
) -> dict:
    team = record.get("team", {})
    all_stats = record.get("all", {})
    home_stats = record.get("home", {})
    away_stats = record.get("away", {})
    all_goals = all_stats.get("goals", {})
    home_goals = home_stats.get("goals", {})
    away_goals = away_stats.get("goals", {})
    return {
        "league_id": league_id,
        "league_name": league_name,
        "league_season": season,
        "team_id": team.get("id"),
        "team_name": team.get("name"),
        "rank": record.get("rank"),
        "points": record.get("points"),
        "goals_diff": record.get("goalsDiff"),
        "group_name": record.get("group"),
        "form": record.get("form"),
        "status": record.get("status"),
        "description": record.get("description"),
        "all_played": all_stats.get("played"),
        "all_wins": all_stats.get("win"),
        "all_draws": all_stats.get("draw"),
        "all_losses": all_stats.get("lose"),
        "all_goals_for": all_goals.get("for"),
        "all_goals_against": all_goals.get("against"),
        "home_played": home_stats.get("played"),
        "home_wins": home_stats.get("win"),
        "home_draws": home_stats.get("draw"),
        "home_losses": home_stats.get("lose"),
        "home_goals_for": home_goals.get("for"),
        "home_goals_against": home_goals.get("against"),
        "away_played": away_stats.get("played"),
        "away_wins": away_stats.get("win"),
        "away_draws": away_stats.get("draw"),
        "away_losses": away_stats.get("lose"),
        "away_goals_for": away_goals.get("for"),
        "away_goals_against": away_goals.get("against"),
        "last_updated": _parse_ts(record.get("update")),
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


def load_standings(standings: list) -> int:
    if not standings:
        return 0
    existing_combos = {
        (row[0], row[1]) for row in spark.sql("""
            SELECT league_id, league_season
            FROM workspace.football_raw.raw_standings
        """).collect()
    }
    new_standings = [
        s for s in standings
        if (s["league_id"], s["league_season"])
        not in existing_combos
    ]
    if not new_standings:
        return 0
    df = spark.createDataFrame(new_standings, schema=STANDING_SCHEMA)
    df.write.mode("append").saveAsTable(
        "workspace.football_raw.raw_standings"
    )
    return len(new_standings)


def main():
    global requests_made
    print("🏆 Fetching standings...")
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
                print(f"\n  Fetching standings for league "
                      f"{league_id} season {season}...")
                response = fetch_from_api(
                    ENDPOINT,
                    params={"league": league_id, "season": season}
                )
                records = response.get("response", [])
                if not records:
                    print("  No standings found — skipping")
                    continue
                all_standings = []
                for record in records:
                    league = record.get("league", {})
                    league_name = league.get("name")
                    for group in league.get("standings", []):
                        for standing in group:
                            all_standings.append(
                                flatten_standing(
                                    league_id, league_name,
                                    season, standing
                                )
                            )
                standing_rows = load_standings(all_standings)
                print(f"  ✅ Loaded {standing_rows} standings")
                update_metadata(
                    f"{ENDPOINT}_{season}",
                    standing_rows, "success", league_id
                )
        print("\n🎉 Standings ingestion complete!")
    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
