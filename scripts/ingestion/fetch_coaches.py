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

API_KEY = dbutils.secrets.get(scope="football", key="api_key")  # noqa: F821

API_BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
ENDPOINT = "coachs"

spark = SparkSession.builder.getOrCreate()


def is_transfer_window() -> bool:
    month = datetime.now().month
    return month in [1, 2, 6, 7, 8]


def should_refetch_coach(team_id: int) -> bool:
    last_ingested = get_last_ingested_at(ENDPOINT, team_id)
    if not last_ingested:
        return True
    days_since = (
        datetime.now(tz=timezone.utc) - last_ingested.replace(tzinfo=timezone.utc)
    ).days
    if is_transfer_window():
        return days_since >= 7
    else:
        return days_since >= 30


def fetch_from_api(endpoint: str, params: dict = {}) -> dict:
    return api_client.fetch_from_api(endpoint, params, headers=HEADERS)


def get_team_ids() -> list:
    result = spark.sql("""
        SELECT DISTINCT team_id
        FROM efua_data_platform.football_raw.raw_teams
        ORDER BY team_id
    """).collect()
    return [row[0] for row in result]


def flatten_coach(record: dict) -> dict:
    birth = record.get("birth", {})
    team = record.get("team", {}) or {}
    birth_date_str = birth.get("date")
    birth_date = None
    if birth_date_str:
        try:
            birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d").date()
        except Exception:
            birth_date = None
    return {
        "coach_id": record.get("id"),
        "coach_name": record.get("name"),
        "firstname": record.get("firstname"),
        "lastname": record.get("lastname"),
        "age": record.get("age"),
        "birth_date": birth_date,
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


def flatten_coach_career(coach_id: int, coach_name: str, career: dict) -> dict:
    team = career.get("team", {})
    start_date_str = career.get("start")
    end_date_str = career.get("end")
    start_date = None
    end_date = None
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except Exception:
            start_date = None
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except Exception:
            end_date = None
    return {
        "coach_id": coach_id,
        "coach_name": coach_name,
        "team_id": team.get("id"),
        "team_name": team.get("name"),
        "start_date": start_date,
        "end_date": end_date,
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


def load_coaches(coaches: list) -> int:
    if not coaches:
        return 0
    valid_coaches = [c for c in coaches if c["coach_id"]]
    if not valid_coaches:
        return 0
    schema = StructType(
        [
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
        ]
    )
    df = spark.createDataFrame(valid_coaches, schema=schema)
    df.createOrReplaceTempView("coaches_staging")
    spark.sql("""
        MERGE INTO efua_data_platform.football_raw.raw_coaches AS target
        USING coaches_staging AS source
        ON target.coach_id = source.coach_id
        WHEN MATCHED THEN UPDATE SET
            current_team_id   = source.current_team_id,
            current_team_name = source.current_team_name,
            ingested_at       = source.ingested_at
        WHEN NOT MATCHED THEN INSERT *
    """)
    return len(valid_coaches)


def load_coach_careers(careers: list, coach_ids: list) -> int:
    if not careers:
        return 0
    ids_str = ", ".join(str(i) for i in coach_ids)
    spark.sql(f"""
        DELETE FROM efua_data_platform.football_raw.raw_coach_careers
        WHERE coach_id IN ({ids_str})
    """)
    schema = StructType(
        [
            StructField("coach_id", IntegerType(), True),
            StructField("coach_name", StringType(), True),
            StructField("team_id", IntegerType(), True),
            StructField("team_name", StringType(), True),
            StructField("start_date", DateType(), True),
            StructField("end_date", DateType(), True),
            StructField("ingested_at", TimestampType(), True),
        ]
    )
    df = spark.createDataFrame(careers, schema=schema)
    df.write.mode("append").saveAsTable(
        "efua_data_platform.football_raw.raw_coach_careers"
    )
    return len(careers)


def log_skipped_team(team_id: int):
    now = datetime.now(tz=timezone.utc)
    spark.sql(f"""
        INSERT INTO efua_data_platform.football_raw.ingestion_metadata
        (endpoint, entity_id, last_ingested_at, rows_inserted,
         requests_used, status, created_at)
        VALUES (
            '{ENDPOINT}', {team_id}, '{now.isoformat()}',
            0, {api_client.get_requests_made()}, 'skipped', '{now.isoformat()}'
        )
    """)


def main():
    print("👔 Fetching coaches...")

    team_ids = get_team_ids()
    in_window = is_transfer_window()
    print(f"  Found {len(team_ids)} unique teams")
    print(f"  Transfer window active: {in_window}")

    current_entity_id = None
    started_at = None
    try:
        for team_id in team_ids:
            api_client.reset_requests_made()

            if not should_refetch_coach(team_id):
                print(f"  Team {team_id} recently checked — skipping")
                continue

            started_at = datetime.now(tz=timezone.utc)
            current_entity_id = team_id
            response = fetch_from_api(ENDPOINT, params={"team": team_id})
            records = response.get("response", [])

            if not records:
                print(f"  No coaches for team {team_id} " f"— logging as skipped")
                log_skipped_team(team_id)
                continue

            coaches = []
            careers = []

            for record in records:
                coaches.append(flatten_coach(record))
                coach_id = record.get("id")
                coach_name = record.get("name")
                for career in record.get("career", []):
                    careers.append(flatten_coach_career(coach_id, coach_name, career))

            coach_ids = [c["coach_id"] for c in coaches if c["coach_id"]]
            coach_rows = load_coaches(coaches)
            career_rows = load_coach_careers(careers, coach_ids)

            print(
                f"  Team {team_id}: ✅ {coach_rows} coaches "
                f"{career_rows} career records"
            )

            update_metadata(
                ENDPOINT,
                coach_rows + career_rows,
                "success",
                team_id,
                started_at=started_at,
            )

        print("\n🎉 Coaches ingestion complete!")

    except Exception as e:
        if current_entity_id:
            update_metadata(ENDPOINT, 0, "failed", current_entity_id, started_at)
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
