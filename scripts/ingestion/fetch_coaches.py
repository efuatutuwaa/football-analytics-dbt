import time
import requests
from datetime import datetime, timezone, date
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, TimestampType, DateType

API_KEY = dbutils.secrets.get(scope="football", key="api_key")
API_BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
ENDPOINT = "coachs"

spark = SparkSession.builder.getOrCreate()
requests_made = 0

COACH_SCHEMA = StructType([
    StructField("coach_id", IntegerType(), True),
    StructField("coach_name", StringType(), True),
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
    StructField("current_team_id", IntegerType(), True),
    StructField("current_team_name", StringType(), True),
    StructField("ingested_at", TimestampType(), True),
])

COACH_CAREER_SCHEMA = StructType([
    StructField("coach_id", IntegerType(), True),
    StructField("coach_name", StringType(), True),
    StructField("team_id", IntegerType(), True),
    StructField("team_name", StringType(), True),
    StructField("start_date", DateType(), True),
    StructField("end_date", DateType(), True),
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


def get_team_ids() -> list:
    result = spark.sql("""
        SELECT DISTINCT team_id
        FROM workspace.football_raw.raw_teams
        ORDER BY team_id
    """).collect()
    return [row[0] for row in result]


def _parse_date(val: str):
    if not val:
        return None
    try:
        return date.fromisoformat(val)
    except (ValueError, TypeError):
        return None


def flatten_coach(record: dict) -> dict:
    birth = record.get("birth", {})
    team = record.get("team", {}) or {}
    return {
        "coach_id": record.get("id"),
        "coach_name": record.get("name"),
        "firstname": record.get("firstname"),
        "lastname": record.get("lastname"),
        "age": record.get("age"),
        "birth_date": _parse_date(birth.get("date")),
        "birth_place": birth.get("place"),
        "birth_country": birth.get("country"),
        "nationality": record.get("nationality"),
        "height": record.get("height"),
        "weight": record.get("weight"),
        "photo_url": record.get("photo"),
        "current_team_id": team.get("id"),
        "current_team_name": team.get("name"),
        "ingested_at": datetime.now(tz=timezone.utc),
    }


def flatten_coach_career(
    coach_id: int, coach_name: str, career: dict
) -> dict:
    team = career.get("team", {})
    return {
        "coach_id": coach_id,
        "coach_name": coach_name,
        "team_id": team.get("id"),
        "team_name": team.get("name"),
        "start_date": _parse_date(career.get("start")),
        "end_date": _parse_date(career.get("end")),
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


def load_coaches(coaches: list) -> int:
    if not coaches:
        return 0
    existing_ids = {
        row[0] for row in spark.sql("""
            SELECT coach_id FROM workspace.football_raw.raw_coaches
        """).collect()
    }
    new_coaches = [
        c for c in coaches
        if c["coach_id"] and c["coach_id"] not in existing_ids
    ]
    if not new_coaches:
        return 0
    df = spark.createDataFrame(new_coaches, schema=COACH_SCHEMA)
    df.write.mode("append").saveAsTable(
        "workspace.football_raw.raw_coaches"
    )
    return len(new_coaches)


def load_coach_careers(careers: list) -> int:
    if not careers:
        return 0
    existing_combos = {
        (row[0], row[1], str(row[2])) for row in spark.sql("""
            SELECT coach_id, team_id, start_date
            FROM workspace.football_raw.raw_coach_careers
        """).collect()
    }
    new_careers = [
        c for c in careers
        if (c["coach_id"], c["team_id"], str(c["start_date"]))
        not in existing_combos
    ]
    if not new_careers:
        return 0
    df = spark.createDataFrame(new_careers, schema=COACH_CAREER_SCHEMA)
    df.write.mode("append").saveAsTable(
        "workspace.football_raw.raw_coach_careers"
    )
    return len(new_careers)


def log_skipped_team(team_id: int):
    now = datetime.now(tz=timezone.utc)
    spark.sql(f"""
        INSERT INTO workspace.football_raw.ingestion_metadata
        (endpoint, entity_id, last_ingested_at, rows_inserted,
         requests_used, status, created_at)
        VALUES (
            '{ENDPOINT}', {team_id}, '{now.isoformat()}',
            0, {requests_made}, 'skipped', '{now.isoformat()}'
        )
    """)


def main():
    global requests_made
    print("👔 Fetching coaches...")
    team_ids = get_team_ids()
    print(f"  Found {len(team_ids)} unique teams")
    try:
        for team_id in team_ids:
            requests_made = 0
            last_ingested_at = get_last_ingested_at(ENDPOINT, team_id)
            if last_ingested_at:
                print(f"  Team {team_id} already processed — skipping")
                continue
            response = fetch_from_api(
                ENDPOINT, params={"team": team_id}
            )
            records = response.get("response", [])
            if not records:
                print(f"  No coaches for team {team_id} — skipping")
                log_skipped_team(team_id)
                continue
            coaches = []
            careers = []
            for record in records:
                coaches.append(flatten_coach(record))
                coach_id = record.get("id")
                coach_name = record.get("name")
                for career in record.get("career", []):
                    careers.append(
                        flatten_coach_career(coach_id, coach_name, career)
                    )
            coach_rows = load_coaches(coaches)
            career_rows = load_coach_careers(careers)
            print(f"  Team {team_id}: ✅ {coach_rows} coaches, "
                  f"{career_rows} career records")
            update_metadata(
                ENDPOINT, coach_rows + career_rows,
                "success", team_id
            )
        print("\n🎉 Coaches ingestion complete!")
    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
