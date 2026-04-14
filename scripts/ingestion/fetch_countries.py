import os
import time
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
from databricks import sql

# ── Config ────────────────────────────────────────────────
load_dotenv()

API_KEY = os.getenv("API_FOOTBALL_KEY")
DATABRICKS_HOST = os.getenv("DATABRICKS_HOST")
DATABRICKS_HTTP_PATH = os.getenv("DATABRICKS_HTTP_PATH")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")

if not all([API_KEY, DATABRICKS_HOST, DATABRICKS_HTTP_PATH, DATABRICKS_TOKEN]):
    raise ValueError("Missing one or more env vars — check your .env file")

API_BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
ENDPOINT = "countries"

# ── Request counter ───────────────────────────────────────
requests_made = 0


# ── API Fetcher ───────────────────────────────────────────
def fetch_from_api(endpoint: str, params: dict = {}) -> dict:
    """Fetch data from API-Football with rate limiting."""
    global requests_made

    url = f"{API_BASE_URL}/{endpoint}"
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    requests_made += 1

    # check remaining requests
    remaining = response.headers.get("x-ratelimit-requests-remaining")
    limit = response.headers.get("x-ratelimit-requests-limit")
    print(f"  API requests remaining: {remaining}/{limit}")

    # stop if running low
    if remaining and int(remaining) < 100:
        raise Exception("⚠️ API request limit almost reached — stopping!")

    time.sleep(0.5)
    return response.json()


# ── Flatten ───────────────────────────────────────────────
def flatten_country(record: dict) -> dict:
    """Flatten API-Football country response into a flat dictionary."""
    return {
        "country_name": record.get("name"),
        "country_code": record.get("code"),
        "country_flag_url": record.get("flag"),
        "ingested_at": datetime.now(tz=timezone.utc),
    }


# ── Incremental check ─────────────────────────────────────
def get_last_ingested_at(cursor, endpoint: str):
    """Get the last ingestion timestamp for this endpoint."""
    cursor.execute("""
        SELECT last_ingested_at
        FROM football_raw.ingestion_metadata
        WHERE endpoint = ?
        AND status = 'success'
        ORDER BY last_ingested_at DESC
        LIMIT 1
    """, [endpoint])
    row = cursor.fetchone()
    return row[0] if row else None


# ── Update metadata ───────────────────────────────────────
def update_metadata(
    cursor,
    endpoint: str,
    rows_inserted: int,
    status: str
):
    """Update ingestion metadata after each run."""
    cursor.execute("""
        INSERT INTO football_raw.ingestion_metadata (
            endpoint,
            last_ingested_at,
            rows_inserted,
            requests_used,
            status,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, [
        endpoint,
        datetime.now(tz=timezone.utc),
        rows_inserted,
        requests_made,
        status,
        datetime.now(tz=timezone.utc),
    ])


# ── Loader ────────────────────────────────────────────────
def load_to_databricks(records: list) -> None:
    """Load flattened country records into football_raw.raw_countries."""
    with sql.connect(
        server_hostname=DATABRICKS_HOST,
        http_path=DATABRICKS_HTTP_PATH,
        access_token=DATABRICKS_TOKEN,
        catalog="workspace"
    ) as connection:
        with connection.cursor() as cursor:

            # check last ingestion
            last_ingested_at = get_last_ingested_at(cursor, ENDPOINT)

            if last_ingested_at:
                print(f"  Countries last ingested at: {last_ingested_at}")
                print("  Countries are static — skipping if already ingested")
                return

            # insert records
            rows_inserted = 0
            for record in records:
                cursor.execute("""
                    INSERT INTO football_raw.raw_countries (
                        country_name,
                        country_code,
                        country_flag_url,
                        ingested_at
                    ) VALUES (?, ?, ?, ?)
                """, [
                    record["country_name"],
                    record["country_code"],
                    record["country_flag_url"],
                    record["ingested_at"],
                ])
                rows_inserted += 1

            # update metadata
            update_metadata(cursor, ENDPOINT, rows_inserted, "success")
            print(f"  ✅ Loaded {rows_inserted} countries")


# ── Main ──────────────────────────────────────────────────
def main():
    print("🌍 Fetching countries...")

    try:
        response = fetch_from_api(ENDPOINT)
        records = response.get("response", [])
        print(f"  Got {len(records)} countries from API")

        flattened = [flatten_country(r) for r in records]
        load_to_databricks(flattened)
        print("🎉 Countries ingestion complete!")

    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()