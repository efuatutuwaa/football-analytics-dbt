# Databricks notebook source
# ruff: noqa: F821, E402

# COMMAND ----------

import subprocess
import sys

subprocess.check_call([sys.executable, "-m", "pip", "install", "dbt-databricks", "-q"])

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import os

host = dbutils.secrets.get("football-analytics", "DATABRICKS_HOST")
http_path = dbutils.secrets.get("football-analytics", "DATABRICKS_HTTP_PATH")
token = dbutils.secrets.get("football-analytics", "DATABRICKS_TOKEN")

profiles_content = f"""
football_analytics:
  target: dev
  outputs:
    dev:
      type: databricks
      host: {host}
      http_path: {http_path}
      token: {token}
      catalog: efua_data_platform
      schema: football_staging
      threads: 4
"""

os.makedirs("/tmp/dbt_profiles", exist_ok=True)
with open("/tmp/dbt_profiles/profiles.yml", "w") as f:
    f.write(profiles_content)

print("profiles.yml written successfully")

# COMMAND ----------

import subprocess

dbt_command = dbutils.widgets.get("dbt_command")

deps_result = subprocess.run(
    "dbt deps --profiles-dir /tmp/dbt_profiles",
    shell=True,
    capture_output=True,
    text=True,
    cwd="/Workspace/Repos/etutuwaa/football-analytics-dbt",
)

print("dbt deps output:")
print(deps_result.stdout)
print(deps_result.stderr)

if deps_result.returncode != 0:
    raise Exception(f"dbt deps failed:\n{deps_result.stderr}")

dbt_result = subprocess.run(
    f"dbt {dbt_command} --profiles-dir /tmp/dbt_profiles",
    shell=True,
    capture_output=True,
    text=True,
    cwd="/Workspace/Repos/etutuwaa/football-analytics-dbt",
)

print(dbt_result.stdout)
print(dbt_result.stderr)

if dbt_result.returncode != 0:
    raise Exception(f"dbt failed:\n{dbt_result.stderr}")
