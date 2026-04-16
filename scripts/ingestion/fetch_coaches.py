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
ENDPOINT = "coachs"

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

    remaining = response.headers.get("x-ratelimit-requests-remaining")
    limit = response.headers.get("x-ratelimit-requests-limit")
    print(f"  API requests remaining: {remaining}/{limit}")

    if remaining and int(remaining) < 100:
        raise Exception("⚠️ API request limit almost reached — stopping!")

    time.sleep(0.5)
    return response.json()


# ── Get team IDs ──────────────────────────────────────────
def get_team_ids(cursor) -> list:
    """Get all unique team IDs from raw_teams."""
    cursor.execute("""
        SELECT DISTINCT team_id
        FROM football_raw.raw_teams
        ORDER BY team_id
    """)
    rows = cursor.fetchall()
    return [row[0] for row in rows]


# ── Flatten coach ─────────────────────────────────────────
def flatten_coach(record: dict) -> dict:
    """Flatten coach profile from API response."""
    birth = record.get("birth", {})
    team = record.get("team", {}) or {}

    return {
        "coach_id": record.get("id"),
        "coach_name": record.get("name"),
        "firstname": record.get("firstname"),
        "lastname": record.get("lastname"),
        "age": record.get("age"),
        "birth_date": birth.get("date"),
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


# ── Flatten coach career ──────────────────────────────────
def flatten_coach_career(
    coach_id: int,
    coach_name: str,
    career: dict
) -> dict:
    """Flatten coach career entry from API response."""
    team = career.get("team", {})

    return {
        "coach_id": coach_id,
        "coach_name": coach_name,
        "team_id": team.get("id"),
        "team_name": team.get("name"),
        "start_date": career.get("start"),
        "end_date": career.get("end"),
        "ingested_at": datetime.now(tz=timezone.utc),
    }


# ── Incremental check ─────────────────────────────────────
def get_last_ingested_at(
    cursor,
    endpoint: str,
    team_id: int = None
):
    """Get the last ingestion timestamp per endpoint and team."""
    if team_id:
        cursor.execute("""
            SELECT last_ingested_at
            FROM football_raw.ingestion_metadata
            WHERE endpoint = ?
            AND entity_id = ?
            AND status IN ('success', 'skipped')
            ORDER BY last_ingested_at DESC
            LIMIT 1
        """, [endpoint, team_id])
    else:
        cursor.execute("""
            SELECT last_ingested_at
            FROM football_raw.ingestion_metadata
            WHERE endpoint = ?
            AND status IN ('success', 'skipped')
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
    status: str,
    team_id: int = None
):
    """Update ingestion metadata after each run."""
    cursor.execute("""
        INSERT INTO football_raw.ingestion_metadata (
            endpoint,
            entity_id,
            last_ingested_at,
            rows_inserted,
            requests_used,
            status,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [
        endpoint,
        team_id,
        datetime.now(tz=timezone.utc),
        rows_inserted,
        requests_made,
        status,
        datetime.now(tz=timezone.utc),
    ])


# ── Load coaches ──────────────────────────────────────────
def load_coaches(cursor, coaches: list) -> int:
    """Load coach profiles into football_raw.raw_coaches."""
    rows_inserted = 0
    for record in coaches:
        cursor.execute("""
            INSERT INTO football_raw.raw_coaches (
                coach_id,
                coach_name,
                firstname,
                lastname,
                age,
                birth_date,
                birth_place,
                birth_country,
                nationality,
                height,
                weight,
                photo_url,
                current_team_id,
                current_team_name,
                ingested_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            record["coach_id"],
            record["coach_name"],
            record["firstname"],
            record["lastname"],
            record["age"],
            record["birth_date"],
            record["birth_place"],
            record["birth_country"],
            record["nationality"],
            record["height"],
            record["weight"],
            record["photo_url"],
            record["current_team_id"],
            record["current_team_name"],
            record["ingested_at"],
        ])
        rows_inserted += 1
    return rows_inserted


# ── Load coach careers ────────────────────────────────────
def load_coach_careers(cursor, careers: list) -> int:
    """Load coach career history into football_raw.raw_coach_careers."""
    rows_inserted = 0
    for record in careers:
        cursor.execute("""
            INSERT INTO football_raw.raw_coach_careers (
                coach_id,
                coach_name,
                team_id,
                team_name,
                start_date,
                end_date,
                ingested_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            record["coach_id"],
            record["coach_name"],
            record["team_id"],
            record["team_name"],
            record["start_date"],
            record["end_date"],
            record["ingested_at"],
        ])
        rows_inserted += 1
    return rows_inserted


# ── Log skipped team ──────────────────────────────────────
def log_skipped_team(team_id: int) -> None:
    """Log teams with no coaches to avoid retrying every run."""
    with sql.connect(
        server_hostname=DATABRICKS_HOST,
        http_path=DATABRICKS_HTTP_PATH,
        access_token=DATABRICKS_TOKEN,
        catalog="workspace"
    ) as connection:
        with connection.cursor() as cursor:
            update_metadata(cursor, ENDPOINT, 0, "skipped", team_id)


# ── Main loader ───────────────────────────────────────────
def load_to_databricks(
    team_id: int,
    coaches: list,
    careers: list
) -> None:
    """Load coaches and careers into Databricks."""
    with sql.connect(
        server_hostname=DATABRICKS_HOST,
        http_path=DATABRICKS_HTTP_PATH,
        access_token=DATABRICKS_TOKEN,
        catalog="workspace"
    ) as connection:
        with connection.cursor() as cursor:

            last_ingested_at = get_last_ingested_at(
                cursor,
                ENDPOINT,
                team_id
            )

            if last_ingested_at:
                print(f"  Team {team_id} already processed — skipping")
                return

            coach_rows = load_coaches(cursor, coaches)
            print(f"  ✅ Loaded {coach_rows} coaches")

            career_rows = load_coach_careers(cursor, careers)
            print(f"  ✅ Loaded {career_rows} career records")

            update_metadata(
                cursor,
                ENDPOINT,
                coach_rows + career_rows,
                "success",
                team_id
            )


# ── Main ──────────────────────────────────────────────────
def main():
    global requests_made
    print("👔 Fetching coaches...")

    with sql.connect(
        server_hostname=DATABRICKS_HOST,
        http_path=DATABRICKS_HTTP_PATH,
        access_token=DATABRICKS_TOKEN,
        catalog="workspace"
    ) as connection:
        with connection.cursor() as cursor:
            team_ids = get_team_ids(cursor)

    print(f"  Found {len(team_ids)} unique teams to fetch coaches for")

    try:
        for team_id in team_ids:
            requests_made = 0

            with sql.connect(
                server_hostname=DATABRICKS_HOST,
                http_path=DATABRICKS_HTTP_PATH,
                access_token=DATABRICKS_TOKEN,
                catalog="workspace"
            ) as connection:
                with connection.cursor() as cursor:
                    if get_last_ingested_at(cursor, ENDPOINT, team_id):
                        print(f"  Team {team_id} already processed — skipping")
                        continue

            response = fetch_from_api(
                ENDPOINT,
                params={"team": team_id}
            )
            records = response.get("response", [])

            if not records:
                print(
                    f"  No coaches found for team {team_id} "
                    f"— logging as skipped"
                )
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

            print(f"  Team {team_id}: {len(coaches)} coaches, "
                  f"{len(careers)} career records")

            load_to_databricks(team_id, coaches, careers)

        print("\n🎉 Coaches ingestion complete!")

    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
