"""
DB Loader
Loads all 7 CSVs into an in-memory DuckDB database and exposes
a query executor used by the SQL generation pipeline.
"""

import os
import duckdb
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

TABLE_FILES = {
    "academic_calendar":   "academic_calendar.csv",
    "sales_transactions":  "sales_transactions.csv",
    "inventory_levels":    "inventory_levels.csv",
    "forecast_vs_actual":  "forecast_vs_actual.csv",
    "supplier_orders":     "supplier_orders.csv",
    "orders":              "orders.csv",
    "subscriptions":       "subscriptions.csv",
}

_conn: duckdb.DuckDBPyConnection | None = None


def get_connection() -> duckdb.DuckDBPyConnection:
    """Return (and lazily initialise) the shared DuckDB connection."""
    global _conn
    if _conn is None:
        _conn = _build_db()
    return _conn


def _build_db() -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(database=":memory:")
    for table, filename in TABLE_FILES.items():
        path = DATA_DIR / filename
        if not path.exists():
            raise FileNotFoundError(
                f"Dataset not found: {path}\n"
                "Run `python scripts/generate_data.py` first."
            )
        df = pd.read_csv(path, low_memory=False)
        # Register as a DuckDB view
        conn.register(table, df)
        print(f"  ✓ Loaded {table} ({len(df):,} rows)")
    return conn


def run_query(sql: str, max_rows: int = 500) -> tuple[pd.DataFrame, str]:
    """
    Execute a SQL query against the DuckDB database.

    Returns:
        (dataframe, error_message)
        On success: (df, "")
        On failure: (empty_df, error_string)
    """
    conn = get_connection()
    try:
        result = conn.execute(sql).fetchdf()
        if len(result) > max_rows:
            result = result.head(max_rows)
        return result, ""
    except Exception as e:
        return pd.DataFrame(), str(e)


def get_table_sample(table: str, n: int = 3) -> pd.DataFrame:
    """Return n sample rows from a table (useful for schema inspection)."""
    df, err = run_query(f"SELECT * FROM {table} LIMIT {n}")
    return df


def list_tables() -> list[str]:
    return list(TABLE_FILES.keys())
