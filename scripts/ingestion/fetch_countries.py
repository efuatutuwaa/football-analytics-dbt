import os
import time
import requests
from datetime import datetime, timezone
from pyspark.sql import SparkSession

API_KEY = os.getenv("API_FOOTBALL_KEY")
from pyspark.sql.types import StructType, StructField, StringType, TimestampType

API_BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
ENDPOINT = "countries"

spark = SparkSession.builder.getOrCreate()
requests_made = 0

COUNTRY_SCHEMA = StructType([
    StructField("country_name", StringType(), True),
    StructField("country_code", StringType(), True),
    StructField("country_flag_url", StringType(), True),
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


def flatten_country(record: dict) -> dict:
    return {
        "country_name": record.get("name"),
        "country_code": record.get("code"),
        "country_flag_url": record.get("flag"),
        "ingested_at": datetime.now(tz=timezone.utc),
    }


def get_last_ingested_at(endpoint: str):
    try:
        result = spark.sql(f"""
            SELECT last_ingested_at
            FROM workspace.football_raw.ingestion_metadata
            WHERE endpoint = '{endpoint}'
            AND status IN ('success', 'skipped')
            ORDER BY last_ingested_at DESC
            LIMIT 1
        """).collect()
        return result[0][0] if result else None
    except Exception:
        return None


def update_metadata(endpoint: str, rows_inserted: int, status: str):
    now = datetime.now(tz=timezone.utc)
    spark.sql(f"""
        INSERT INTO workspace.football_raw.ingestion_metadata
        (endpoint, entity_id, last_ingested_at, rows_inserted,
         requests_used, status, created_at)
        VALUES (
            '{endpoint}', NULL, '{now.isoformat()}',
            {rows_inserted}, {requests_made}, '{status}',
            '{now.isoformat()}'
        )
    """)


def load_countries(countries: list) -> int:
    if not countries:
        return 0
    existing_names = {
        row[0] for row in spark.sql("""
            SELECT country_name
            FROM workspace.football_raw.raw_countries
        """).collect()
    }
    new_countries = [
        c for c in countries
        if c["country_name"] and c["country_name"] not in existing_names
    ]
    if not new_countries:
        print("  No new countries to load")
        return 0
    df = spark.createDataFrame(new_countries, schema=COUNTRY_SCHEMA)
    df.write.mode("append").saveAsTable(
        "workspace.football_raw.raw_countries"
    )
    return len(new_countries)


def main():
    print("🌍 Fetching countries...")
    last_ingested_at = get_last_ingested_at(ENDPOINT)
    if last_ingested_at:
        print("  Countries already ingested — skipping")
        return
    try:
        response = fetch_from_api(ENDPOINT)
        records = response.get("response", [])
        print(f"  Got {len(records)} countries from API")
        countries = [flatten_country(r) for r in records]
        rows_inserted = load_countries(countries)
        print(f"  ✅ Loaded {rows_inserted} countries")
        update_metadata(ENDPOINT, rows_inserted, "success")
        print("🎉 Countries ingestion complete!")
    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
