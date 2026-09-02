"""
Tests for PostgreSQL database connection, query execution, and dynamic schema introspection.
"""

import pytest
from app.database.connection import test_connection as check_db_connection, execute_query
from app.database.schema import inspect_schema, get_database_schema, format_schema_for_llm


def test_db_connection():
    """Verify that PostgreSQL connection succeeds."""
    connected = check_db_connection()
    assert connected is True


def test_schema_introspection_tables():
    """Verify that all four core tables exist in schema introspection."""
    schema_dict = inspect_schema()
    expected_tables = {"customers", "products", "orders", "order_items"}
    
    assert expected_tables.issubset(set(schema_dict.keys())), (
        f"Missing expected tables. Found: {list(schema_dict.keys())}"
    )


def test_schema_formatting():
    """Verify that schema formatting generates clean text with columns and keys."""
    schema_text = get_database_schema(force_refresh=True)
    
    assert "Table: customers" in schema_text
    assert "customer_id" in schema_text
    assert "city" in schema_text
    assert "Table: orders" in schema_text
    assert "Table: products" in schema_text
    assert "Table: order_items" in schema_text


def test_execute_query_success():
    """Verify executing a valid SELECT returns columns, dict rows, and raw rows."""
    res = execute_query("SELECT customer_id, name FROM customers ORDER BY customer_id LIMIT 2;")
    assert isinstance(res, dict)
    assert res["columns"] == ["customer_id", "name"]
    assert len(res["rows"]) == 2
    assert res["rows"][0]["name"] == "Rahul Sharma"


def test_execute_query_error_handling():
    """Verify that executing a bad SQL query returns a formatted DATABASE_ERROR string."""
    res = execute_query("SELECT non_existent_column FROM non_existent_table;")
    assert isinstance(res, str)
    assert res.startswith("DATABASE_ERROR:")
