import time
import requests
from datetime import datetime, timezone
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, TimestampType, BooleanType

API_KEY = dbutils.secrets.get(scope="football", key="api_key")  # noqa: F821
API_BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
ENDPOINT = "fixtures/players"

spark = SparkSession.builder.getOrCreate()
requests_made = 0

PLAYER_STATS_SCHEMA = StructType([
    StructField("fixture_id", IntegerType(), True),
    StructField("team_id", IntegerType(), True),
    StructField("team_name", StringType(), True),
    StructField("player_id", IntegerType(), True),
    StructField("player_name", StringType(), True),
    StructField("minutes_played", IntegerType(), True),
    StructField("jersey_number", IntegerType(), True),
    StructField("position", StringType(), True),
    StructField("rating", StringType(), True),
    StructField("is_captain", BooleanType(), True),
    StructField("is_substitute", BooleanType(), True),
    StructField("offsides", IntegerType(), True),
    StructField("shots_total", IntegerType(), True),
    StructField("shots_on_target", IntegerType(), True),
    StructField("goals_scored", IntegerType(), True),
    StructField("goals_conceded", IntegerType(), True),
    StructField("assists", IntegerType(), True),
    StructField("saves", IntegerType(), True),
    StructField("passes_total", IntegerType(), True),
    StructField("passes_key", IntegerType(), True),
    StructField("pass_accuracy", StringType(), True),
    StructField("tackles_total", IntegerType(), True),
    StructField("blocks", IntegerType(), True),
    StructField("interceptions", IntegerType(), True),
    StructField("duels_total", IntegerType(), True),
    StructField("duels_won", IntegerType(), True),
    StructField("dribbles_attempted", IntegerType(), True),
    StructField("dribbles_success", IntegerType(), True),
    StructField("dribbles_past", IntegerType(), True),
    StructField("fouls_drawn", IntegerType(), True),
    StructField("fouls_committed", IntegerType(), True),
    StructField("yellow_cards", IntegerType(), True),
    StructField("red_cards", IntegerType(), True),
    StructField("penalty_won", IntegerType(), True),
    StructField("penalty_committed", IntegerType(), True),
    StructField("penalty_scored", IntegerType(), True),
    StructField("penalty_missed", IntegerType(), True),
    StructField("penalty_saved", IntegerType(), True),
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
            FROM efua_data_platform.football_raw.raw_player_statistics
        """).collect()
        return {row[0] for row in result}
    except Exception:
        return set()


def flatten_player_statistics(
    fixture_id: int, team_id: int,
    team_name: str, player: dict, stats: dict
) -> dict:
    games = stats.get("games", {})
    shots = stats.get("shots", {})
    goals = stats.get("goals", {})
    passes = stats.get("passes", {})
    tackles = stats.get("tackles", {})
    duels = stats.get("duels", {})
    dribbles = stats.get("dribbles", {})
    fouls = stats.get("fouls", {})
    cards = stats.get("cards", {})
    penalty = stats.get("penalty", {})
    return {
        "fixture_id": fixture_id,
        "team_id": team_id,
        "team_name": team_name,
        "player_id": player.get("id"),
        "player_name": player.get("name"),
        "minutes_played": games.get("minutes"),
        "jersey_number": games.get("number"),
        "position": games.get("position"),
        "rating": str(games.get("rating")) if games.get("rating") else None,
        "is_captain": games.get("captain"),
        "is_substitute": games.get("substitute"),
        "offsides": stats.get("offsides"),
        "shots_total": shots.get("total"),
        "shots_on_target": shots.get("on"),
        "goals_scored": goals.get("total"),
        "goals_conceded": goals.get("conceded"),
        "assists": goals.get("assists"),
        "saves": goals.get("saves"),
        "passes_total": passes.get("total"),
        "passes_key": passes.get("key"),
        "pass_accuracy": str(passes.get("accuracy")) if passes.get("accuracy") else None,
        "tackles_total": tackles.get("total"),
        "blocks": tackles.get("blocks"),
        "interceptions": tackles.get("interceptions"),
        "duels_total": duels.get("total"),
        "duels_won": duels.get("won"),
        "dribbles_attempted": dribbles.get("attempts"),
        "dribbles_success": dribbles.get("success"),
        "dribbles_past": dribbles.get("past"),
        "fouls_drawn": fouls.get("drawn"),
        "fouls_committed": fouls.get("committed"),
        "yellow_cards": cards.get("yellow"),
        "red_cards": cards.get("red"),
        "penalty_won": penalty.get("won"),
        "penalty_committed": penalty.get("commited"),
        "penalty_scored": penalty.get("scored"),
        "penalty_missed": penalty.get("missed"),
        "penalty_saved": penalty.get("saved"),
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


def load_player_statistics(stats: list) -> int:
    if not stats:
        return 0
    df = spark.createDataFrame(stats, schema=PLAYER_STATS_SCHEMA)
    df.write.mode("append").saveAsTable(
        "efua_data_platform.football_raw.raw_player_statistics"
    )
    return len(stats)


def main():
    global requests_made
    print("👤 Fetching player statistics...")
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
            print(f"\n  Fetching player stats for league {league_id} "
                  f"season {season}: {len(new_fixture_ids)} new fixture(s) "
                  f"(of {len(all_fixture_ids)} total)...")
            all_stats = []
            total_rows = 0
            for fixture_id in new_fixture_ids:
                response = fetch_from_api(
                    "fixtures/players",
                    params={"fixture": fixture_id}
                )
                records = response.get("response", [])
                for record in records:
                    team = record.get("team", {})
                    team_id = team.get("id")
                    team_name = team.get("name")
                    for player_record in record.get("players", []):
                        player = player_record.get("player", {})
                        statistics = player_record.get(
                            "statistics", [{}]
                        )[0]
                        all_stats.append(
                            flatten_player_statistics(
                                fixture_id, team_id,
                                team_name, player, statistics
                            )
                        )
                # batch write every 100 fixtures (approx 44 players each)
                if len(all_stats) >= 100 * 44:
                    stat_rows = load_player_statistics(all_stats)
                    total_rows += stat_rows
                    ingested_fixture_ids.update(
                        s["fixture_id"] for s in all_stats
                    )
                    print(f"  ✅ Batch loaded {stat_rows} player stats")
                    all_stats = []
            if all_stats:
                stat_rows = load_player_statistics(all_stats)
                total_rows += stat_rows
                ingested_fixture_ids.update(
                    s["fixture_id"] for s in all_stats
                )
                print(f"  ✅ Loaded {stat_rows} player stats")
            update_metadata(
                f"{ENDPOINT}_{season}",
                total_rows, "success", league_id,
                started_at=started_at
            )
        print("\n🎉 Player statistics ingestion complete!")
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
