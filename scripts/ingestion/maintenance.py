from pyspark.sql import SparkSession

CATALOG = "efua_data_platform"
SCHEMA = "football_raw"

TABLES = [
    "raw_fixtures",
    "raw_fixture_scores",
    "raw_fixture_events",
    "raw_fixture_lineups",
    "raw_fixture_lineup_players",
    "raw_fixture_statistics",
    "raw_player_statistics",
    "raw_standings",
    "ingestion_metadata",
]

VACUUM_RETAIN_HOURS = 168  # 7 days — Delta minimum safe retention

spark = SparkSession.builder.getOrCreate()


def vacuum(table: str):
    full_name = f"{CATALOG}.{SCHEMA}.{table}"
    print(f"  Running VACUUM on {full_name}...")
    spark.sql(f"VACUUM {full_name} RETAIN {VACUUM_RETAIN_HOURS} HOURS")
    print("  ✅ VACUUM complete")


def optimize(table: str):
    full_name = f"{CATALOG}.{SCHEMA}.{table}"
    print(f"  Running OPTIMIZE on {full_name}...")
    spark.sql(f"OPTIMIZE {full_name}")
    print("  ✅ OPTIMIZE complete")


def main():
    print("🧹 Starting maintenance...")
    for table in TABLES:
        try:
            vacuum(table)
            optimize(table)
        except Exception as e:
            print(f"  ⚠️  {table}: {e}")
    print("\n🎉 Maintenance complete!")


if __name__ == "__main__":
    main()
