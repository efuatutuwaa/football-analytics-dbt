"""Databricks SQL connection for Streamlit.

Connection settings come from **app/.env** (not dbt profiles.yml). python-dotenv loads
the file into process env vars; `os.environ` / `os.getenv` read them — that is the
standard pattern (same values you use in Databricks SQL, different file than dbt).

Required in app/.env:
  DATABRICKS_HOST, DATABRICKS_HTTP_PATH, DATABRICKS_TOKEN
Optional (must match where dbt built your tables):
  DATABRICKS_CATALOG, DATABRICKS_MARTS_SCHEMA, DATABRICKS_CORE_SCHEMA, DATABRICKS_OPS_SCHEMA
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import pandas as pd
from dotenv import load_dotenv

# Load app/.env when this module is imported (pages import db before streamlit_app runs).
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _catalog() -> str:
    return os.getenv("DATABRICKS_CATALOG", "main")


def marts_table(name: str) -> str:
    schema = os.getenv("DATABRICKS_MARTS_SCHEMA", "football_marts")
    return f"`{_catalog()}`.`{schema}`.`{name}`"


def core_table(name: str) -> str:
    schema = os.getenv("DATABRICKS_CORE_SCHEMA", "football_core")
    return f"`{_catalog()}`.`{schema}`.`{name}`"


def ops_table(name: str) -> str:
    schema = os.getenv("DATABRICKS_OPS_SCHEMA", "football_ops")
    return f"`{_catalog()}`.`{schema}`.`{name}`"


@contextmanager
def databricks_connection() -> Iterator[Any]:
    from databricks import sql

    host = os.environ["DATABRICKS_HOST"]
    http_path = os.environ["DATABRICKS_HTTP_PATH"]
    token = os.environ["DATABRICKS_TOKEN"]

    conn = sql.connect(
        server_hostname=host,
        http_path=http_path,
        access_token=token,
    )
    try:
        yield conn
    finally:
        conn.close()


def run_query(sql: str) -> pd.DataFrame:
    with databricks_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            if cursor.description is None:
                return pd.DataFrame()
            column_names: list[str] = [str(col[0]) for col in cursor.description]
            rows = cursor.fetchall()
    return pd.DataFrame.from_records(rows, columns=pd.Index(column_names))
