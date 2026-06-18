import api_client
from datetime import datetime, timezone
from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    IntegerType,
    DateType,
    TimestampType,
)

from constants import LEAGUE_IDS, SEASONS

API_KEY = dbutils.secrets.get(scope="football", key="api_key")  # noqa: F821

API_BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
ENDPOINT = "players"

spark = SparkSession.builder.getOrCreate()


def should_refetch(endpoint: str, league_id: int, season: int) -> bool:
    last_ingested = get_last_ingested_at(f"{endpoint}_{season}", league_id)
    if not last_ingested:
        return True
    days_since = (
        datetime.now(tz=timezone.utc) - last_ingested.replace(tzinfo=timezone.utc)
    ).days
    return days_since >= 365


def fetch_from_api(endpoint: str, params: dict = {}) -> dict:
    return api_client.fetch_from_api(endpoint, params, headers=HEADERS)


def fetch_all_pages(league_id: int, season: int) -> list:
    all_records = []
    page = 1
    while True:
        print(f"    Fetching page {page}...")
        response = fetch_from_api(
            ENDPOINT, params={"league": league_id, "season": season, "page": page}
        )
        records = response.get("response", [])
        if not records:
            break
        all_records.extend(records)
        paging = response.get("paging", {})
        current = paging.get("current", 1)
        total = paging.get("total", 1)
        print(f"    Page {current}/{total} — {len(records)} players")
        if current >= total:
            break
        page += 1
    return all_records


def flatten_player(record: dict) -> dict:
    player = record.get("player", {})
    birth = player.get("birth", {})
    birth_date_str = birth.get("date")
    birth_date = None
    if birth_date_str:
        try:
            birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d").date()
        except Exception:
            birth_date = None
    return {
        "player_id": player.get("id"),
        "player_name": player.get("name"),
        "firstname": player.get("firstname"),
        "lastname": player.get("lastname"),
        "age": player.get("age"),
        "birth_date": birth_date,
        "birth_place": birth.get("place"),
        "birth_country": birth.get("country"),
        "nationality": player.get("nationality"),
        "height": player.get("height"),
        "weight": player.get("weight"),
        "photo_url": player.get("photo"),
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


def update_metadata(
    endpoint: str,
    rows_inserted: int,
    status: str,
    entity_id: int = None,
    started_at: datetime = None,
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
            {rows_inserted}, {api_client.get_requests_made()}, '{status}',
            '{now.isoformat()}', {started_val}
        )
    """)


def load_players(players: list) -> int:
    if not players:
        return 0
    existing_ids = {
        row[0]
        for row in spark.sql("""
            SELECT player_id
            FROM efua_data_platform.football_raw.raw_players
        """).collect()
    }
    new_players = [
        p for p in players if p["player_id"] and p["player_id"] not in existing_ids
    ]
    if not new_players:
        print("  No new players to load")
        return 0
    schema = StructType(
        [
            StructField("player_id", IntegerType(), True),
            StructField("player_name", StringType(), True),
            StructField("firstname", StringType(), True),
            StructField("lastname", StringType(), True),
            StructField("age", IntegerType(), True),
            StructField("birth_date", DateType(), True),
            StructField("birth_place", StringType(), True),
            StructField("birth_country", StringType(), True),
            StructField("nationality", StringType(), True),
            StructField("height", StringType(), True),
            StructField("weight", StringType(), True),
            StructField("photo_url", StringType(), True),
            StructField("ingested_at", TimestampType(), True),
        ]
    )
    df = spark.createDataFrame(new_players, schema=schema)
    df.write.mode("append").saveAsTable("efua_data_platform.football_raw.raw_players")
    return len(new_players)


def main():
    print("👤 Fetching players...")
    current_endpoint = None
    current_entity_id = None
    started_at = None

    try:
        for league_id in LEAGUE_IDS:
            for season in SEASONS:
                api_client.reset_requests_made()

                if not should_refetch(ENDPOINT, league_id, season):
                    print(
                        f"  League {league_id} season {season} "
                        f"recently fetched — skipping"
                    )
                    continue

                started_at = datetime.now(tz=timezone.utc)
                current_endpoint = f"{ENDPOINT}_{season}"
                current_entity_id = league_id
                print(
                    f"\n  Fetching players for league "
                    f"{league_id} season {season}..."
                )
                records = fetch_all_pages(league_id, season)

                if not records:
                    print("  No players found — skipping")
                    continue

                players = [flatten_player(r) for r in records]
                print(f"  Got {len(players)} players")

                player_rows = load_players(players)
                print(f"  ✅ Loaded {player_rows} new players")

                update_metadata(
                    f"{ENDPOINT}_{season}",
                    player_rows,
                    "success",
                    league_id,
                    started_at=started_at,
                )

        print("\n🎉 Players ingestion complete!")

    except Exception as e:
        if current_endpoint:
            update_metadata(
                current_endpoint, 0, "failed", current_entity_id, started_at
            )
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
