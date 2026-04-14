import os
from dotenv import load_dotenv
from databricks import sql

# ── Config ────────────────────────────────────────────────
load_dotenv()

DATABRICKS_HOST = os.getenv("DATABRICKS_HOST")
DATABRICKS_HTTP_PATH = os.getenv("DATABRICKS_HTTP_PATH")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")

if not all([DATABRICKS_HOST, DATABRICKS_HTTP_PATH, DATABRICKS_TOKEN]):
    raise ValueError("Missing one or more Databricks env vars — check your .env file")

# ── DDL Statements ────────────────────────────────────────
DDL_STATEMENTS = [

    # Schema
    "CREATE SCHEMA IF NOT EXISTS football_raw",

    # Countries
    """
    CREATE TABLE IF NOT EXISTS football_raw.raw_countries (
        country_name STRING,
        country_code STRING,
        country_flag_url STRING,
        ingested_at TIMESTAMP
    ) USING DELTA
    """,

    # Leagues
    """
    CREATE TABLE IF NOT EXISTS football_raw.raw_leagues (
        league_id INT,
        league_name STRING,
        league_type STRING,
        league_logo_url STRING,
        country_name STRING,
        country_code STRING,
        country_flag_url STRING,
        ingested_at TIMESTAMP
    ) USING DELTA
    """,

    # League Seasons
    """
    CREATE TABLE IF NOT EXISTS football_raw.raw_league_seasons (
        league_id INT,
        season_year INT,
        season_start DATE,
        season_end DATE,
        is_current_season BOOLEAN,
        coverage_fixtures_events BOOLEAN,
        coverage_fixtures_lineups BOOLEAN,
        coverage_standings BOOLEAN,
        coverage_players BOOLEAN,
        coverage_top_scorers BOOLEAN,
        coverage_injuries BOOLEAN,
        coverage_predictions BOOLEAN,
        coverage_odds BOOLEAN,
        ingested_at TIMESTAMP
    ) USING DELTA
    """,

    # Teams
    """
    CREATE TABLE IF NOT EXISTS football_raw.raw_teams (
        team_id INT,
        team_name STRING,
        team_code STRING,
        team_country STRING,
        founded_year INT,
        is_national_team BOOLEAN,
        team_logo_url STRING,
        ingested_at TIMESTAMP
    ) USING DELTA
    """,

    # Venues
    """
    CREATE TABLE IF NOT EXISTS football_raw.raw_venues (
        venue_id INT,
        venue_name STRING,
        venue_address STRING,
        venue_city STRING,
        venue_capacity INT,
        venue_surface STRING,
        venue_image_url STRING,
        ingested_at TIMESTAMP
    ) USING DELTA
    """,

    # Coaches
    """
    CREATE TABLE IF NOT EXISTS football_raw.raw_coaches (
        coach_id INT,
        coach_name STRING,
        firstname STRING,
        lastname STRING,
        age INT,
        birth_date DATE,
        birth_place STRING,
        birth_country STRING,
        nationality STRING,
        height STRING,
        weight STRING,
        photo_url STRING,
        current_team_id INT,
        current_team_name STRING,
        ingested_at TIMESTAMP
    ) USING DELTA
    """,

    # Coach Careers
    """
    CREATE TABLE IF NOT EXISTS football_raw.raw_coach_careers (
        coach_id INT,
        coach_name STRING,
        team_id INT,
        team_name STRING,
        start_date DATE,
        end_date DATE,
        ingested_at TIMESTAMP
    ) USING DELTA
    """,

    # Players
    """
    CREATE TABLE IF NOT EXISTS football_raw.raw_players (
        player_id INT,
        player_name STRING,
        firstname STRING,
        lastname STRING,
        age INT,
        birth_date DATE,
        birth_place STRING,
        birth_country STRING,
        nationality STRING,
        height STRING,
        weight STRING,
        jersey_number INT,
        position STRING,
        photo_url STRING,
        ingested_at TIMESTAMP
    ) USING DELTA
    """,

    # Team Squads
    """
    CREATE TABLE IF NOT EXISTS football_raw.raw_team_squads (
        team_id INT,
        team_name STRING,
        player_id INT,
        player_name STRING,
        player_age INT,
        jersey_number INT,
        position STRING,
        photo_url STRING,
        ingested_at TIMESTAMP
    ) USING DELTA
    """,

    # Fixtures
    """
    CREATE TABLE IF NOT EXISTS football_raw.raw_fixtures (
        fixture_id INT,
        referee STRING,
        timezone STRING,
        match_date TIMESTAMP,
        match_timestamp BIGINT,
        first_period_start BIGINT,
        second_period_start BIGINT,
        venue_id INT,
        venue_name STRING,
        venue_city STRING,
        status_long STRING,
        status_short STRING,
        elapsed_minutes INT,
        extra_time INT,
        league_id INT,
        league_name STRING,
        league_country STRING,
        league_season INT,
        league_round STRING,
        home_team_id INT,
        home_team_name STRING,
        home_team_winner BOOLEAN,
        away_team_id INT,
        away_team_name STRING,
        away_team_winner BOOLEAN,
        ingested_at TIMESTAMP
    ) USING DELTA
    """,

    # Fixture Scores
    """
    CREATE TABLE IF NOT EXISTS football_raw.raw_fixture_scores (
        fixture_id INT,
        halftime_home INT,
        halftime_away INT,
        fulltime_home INT,
        fulltime_away INT,
        extratime_home INT,
        extratime_away INT,
        penalty_home INT,
        penalty_away INT,
        ingested_at TIMESTAMP
    ) USING DELTA
    """,

    # Fixture Events
    """
    CREATE TABLE IF NOT EXISTS football_raw.raw_fixture_events (
        fixture_id INT,
        elapsed_minutes INT,
        extra_minutes INT,
        team_id INT,
        team_name STRING,
        player_id INT,
        player_name STRING,
        assist_player_id INT,
        assist_player_name STRING,
        event_type STRING,
        event_detail STRING,
        comments STRING,
        ingested_at TIMESTAMP
    ) USING DELTA
    """,

    # Fixture Statistics
    """
    CREATE TABLE IF NOT EXISTS football_raw.raw_fixture_statistics (
        fixture_id INT,
        team_id INT,
        team_name STRING,
        shots_on_goal INT,
        shots_off_goal INT,
        total_shots INT,
        blocked_shots INT,
        shots_inside_box INT,
        shots_outside_box INT,
        fouls INT,
        corner_kicks INT,
        offsides INT,
        ball_possession STRING,
        yellow_cards INT,
        red_cards INT,
        goalkeeper_saves INT,
        total_passes INT,
        accurate_passes INT,
        pass_accuracy STRING,
        ingested_at TIMESTAMP
    ) USING DELTA
    """,

    # Fixture Lineups
    """
    CREATE TABLE IF NOT EXISTS football_raw.raw_fixture_lineups (
        fixture_id INT,
        team_id INT,
        team_name STRING,
        formation STRING,
        coach_id INT,
        coach_name STRING,
        ingested_at TIMESTAMP
    ) USING DELTA
    """,

    # Fixture Lineup Players
    """
    CREATE TABLE IF NOT EXISTS football_raw.raw_fixture_lineup_players (
        fixture_id INT,
        team_id INT,
        player_id INT,
        player_name STRING,
        jersey_number INT,
        position STRING,
        grid_position STRING,
        is_starter BOOLEAN,
        ingested_at TIMESTAMP
    ) USING DELTA
    """,

    # Player Statistics
    """
    CREATE TABLE IF NOT EXISTS football_raw.raw_player_statistics (
        fixture_id INT,
        team_id INT,
        team_name STRING,
        player_id INT,
        player_name STRING,
        minutes_played INT,
        jersey_number INT,
        position STRING,
        rating STRING,
        is_captain BOOLEAN,
        is_substitute BOOLEAN,
        offsides INT,
        shots_total INT,
        shots_on_target INT,
        goals_scored INT,
        goals_conceded INT,
        assists INT,
        saves INT,
        passes_total INT,
        passes_key INT,
        pass_accuracy STRING,
        tackles_total INT,
        blocks INT,
        interceptions INT,
        duels_total INT,
        duels_won INT,
        dribbles_attempted INT,
        dribbles_success INT,
        dribbles_past INT,
        fouls_drawn INT,
        fouls_committed INT,
        yellow_cards INT,
        red_cards INT,
        penalty_won INT,
        penalty_committed INT,
        penalty_scored INT,
        penalty_missed INT,
        penalty_saved INT,
        ingested_at TIMESTAMP
    ) USING DELTA
    """,

    # Transfers
    """
    CREATE TABLE IF NOT EXISTS football_raw.raw_transfers (
        player_id INT,
        player_name STRING,
        transfer_date DATE,
        transfer_type STRING,
        team_in_id INT,
        team_in_name STRING,
        team_out_id INT,
        team_out_name STRING,
        last_updated TIMESTAMP,
        ingested_at TIMESTAMP
    ) USING DELTA
    """,

    # Standings
    """
    CREATE TABLE IF NOT EXISTS football_raw.raw_standings (
        league_id INT,
        league_name STRING,
        league_season INT,
        team_id INT,
        team_name STRING,
        rank INT,
        points INT,
        goals_diff INT,
        group_name STRING,
        form STRING,
        status STRING,
        description STRING,
        all_played INT,
        all_wins INT,
        all_draws INT,
        all_losses INT,
        all_goals_for INT,
        all_goals_against INT,
        home_played INT,
        home_wins INT,
        home_draws INT,
        home_losses INT,
        home_goals_for INT,
        home_goals_against INT,
        away_played INT,
        away_wins INT,
        away_draws INT,
        away_losses INT,
        away_goals_for INT,
        away_goals_against INT,
        last_updated TIMESTAMP,
        ingested_at TIMESTAMP
    ) USING DELTA
    """,

    # Ingestion Metadata
    """
    CREATE TABLE IF NOT EXISTS football_raw.ingestion_metadata (
        endpoint STRING,
        last_ingested_at TIMESTAMP,
        rows_inserted INT,
        status STRING,
        created_at TIMESTAMP
    ) USING DELTA
    """,
]

# ── Main ──────────────────────────────────────────────────
def create_tables():
    print("🏈 Creating football_raw tables...")

    with sql.connect(
        server_hostname=DATABRICKS_HOST,
        http_path=DATABRICKS_HTTP_PATH,
        access_token=DATABRICKS_TOKEN,
        catalog="workspace"
    ) as connection:
        with connection.cursor() as cursor:
            for statement in DDL_STATEMENTS:
                if "CREATE TABLE" in statement:
                    table_name = [
                        line.strip()
                        for line in statement.split("\n")
                        if "CREATE TABLE" in line
                    ][0].split(".")[-1].split(" ")[0]
                    print(f"  Creating {table_name}...")
                    cursor.execute(statement)
                    print(f"  ✅ {table_name} created")
                else:
                    cursor.execute(statement)

    print("🎉 All tables created successfully!")

if __name__ == "__main__":
    create_tables()
