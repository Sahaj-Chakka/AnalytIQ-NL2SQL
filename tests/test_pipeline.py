"""
Tests for AnalytIQ SQL Generator and RAG Engine.
Run: pytest tests/ -v
"""

import os
import sys
import pytest
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.db_loader import run_query, get_table_sample, list_tables
from backend.schema_registry import SCHEMA_REGISTRY, get_schema_text, get_table_list


# ── DB Tests ──────────────────────────────────────────────────────────────────
class TestDatabase:
    def test_all_tables_load(self):
        tables = list_tables()
        assert len(tables) == 7
        for t in tables:
            df, err = run_query(f"SELECT COUNT(*) AS n FROM {t}")
            assert err == "", f"Error querying {t}: {err}"
            assert df.iloc[0]["n"] > 0, f"Table {t} is empty"

    def test_academic_calendar_has_366_rows(self):
        df, err = run_query("SELECT COUNT(*) AS n FROM academic_calendar")
        assert err == ""
        assert df.iloc[0]["n"] == 366   # 2024 is a leap year

    def test_sales_transactions_columns(self):
        df = get_table_sample("sales_transactions", n=1)
        expected = ["date","outlet","category","sku","qty_sold","unit_price","revenue","waste_qty"]
        for col in expected:
            assert col in df.columns, f"Missing column: {col}"

    def test_inventory_status_values(self):
        df, err = run_query(
            "SELECT DISTINCT inventory_status FROM inventory_levels ORDER BY 1"
        )
        assert err == ""
        valid = {"Healthy", "Watch", "Overstock", "Stockout Risk"}
        returned = set(df["inventory_status"].tolist())
        assert returned.issubset(valid)

    def test_calendar_traffic_multiplier_range(self):
        df, err = run_query(
            "SELECT MIN(traffic_multiplier) AS mn, MAX(traffic_multiplier) AS mx "
            "FROM academic_calendar"
        )
        assert err == ""
        assert df.iloc[0]["mn"] >= 0.0
        assert df.iloc[0]["mx"] <= 3.0

    def test_join_sales_calendar(self):
        sql = """
            SELECT s.outlet, c.semester, SUM(s.revenue) AS total_revenue
            FROM sales_transactions s
            JOIN academic_calendar c ON s.date = c.date
            WHERE c.semester = 'Fall'
            GROUP BY s.outlet, c.semester
            ORDER BY total_revenue DESC
            LIMIT 5
        """
        df, err = run_query(sql)
        assert err == "", f"Join query failed: {err}"
        assert len(df) > 0
        assert "outlet" in df.columns

    def test_overstock_query(self):
        sql = """
            SELECT outlet, category, COUNT(*) AS overstock_days
            FROM inventory_levels
            WHERE overstock_flag = true
            GROUP BY outlet, category
            ORDER BY overstock_days DESC
            LIMIT 10
        """
        df, err = run_query(sql)
        assert err == ""
        assert "overstock_days" in df.columns

    def test_supplier_on_time_rate(self):
        sql = """
            SELECT supplier,
                   ROUND(AVG(CAST(on_time_delivery AS DOUBLE)) * 100, 1) AS on_time_pct
            FROM supplier_orders
            GROUP BY supplier
            ORDER BY on_time_pct DESC
        """
        df, err = run_query(sql)
        assert err == ""
        assert len(df) >= 1

    def test_saas_churn_by_plan(self):
        sql = """
            SELECT plan, COUNT(*) AS churns
            FROM subscriptions
            WHERE event_type = 'churn'
            GROUP BY plan
            ORDER BY churns DESC
        """
        df, err = run_query(sql)
        assert err == ""
        assert "churns" in df.columns

    def test_exam_period_sales_spike(self):
        sql = """
            SELECT c.is_exam_period,
                   ROUND(AVG(s.revenue), 2) AS avg_revenue
            FROM sales_transactions s
            JOIN academic_calendar c ON s.date = c.date
            GROUP BY c.is_exam_period
        """
        df, err = run_query(sql)
        assert err == ""
        assert len(df) == 2   # True / False


# ── Schema Registry Tests ──────────────────────────────────────────────────────
class TestSchemaRegistry:
    def test_all_tables_in_registry(self):
        registered = get_table_list()
        db_tables  = list_tables()
        for t in db_tables:
            assert t in registered, f"{t} missing from schema registry"

    def test_schema_text_not_empty(self):
        for table in get_table_list():
            text = get_schema_text(table)
            assert len(text) > 100, f"Schema text too short for {table}"
            assert table in text

    def test_sample_questions_present(self):
        for table, schema in SCHEMA_REGISTRY.items():
            assert "sample_questions" in schema
            assert len(schema["sample_questions"]) >= 2, \
                f"{table} needs at least 2 sample questions"

    def test_column_descriptions_complete(self):
        for table, schema in SCHEMA_REGISTRY.items():
            df = get_table_sample(table, n=1)
            for col in df.columns:
                assert col in schema["columns"], \
                    f"Column '{col}' in {table} not documented in registry"
