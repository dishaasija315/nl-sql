"""
Unit tests for SQL Safety Validator.
Verifies that only read-only SELECT/CTE queries pass, and all destructive operations are blocked.
"""

import pytest
from app.database.validator import validate_sql, is_safe_sql


def test_valid_select_query():
    """Simple SELECT queries must be allowed."""
    query = "SELECT customer_id, name, city FROM customers WHERE city = 'Delhi';"
    is_valid, reason = validate_sql(query)
    assert is_valid is True
    assert reason == ""
    assert is_safe_sql(query) is True


def test_valid_aggregate_select():
    """Aggregate queries with joins, group by, and order by must be allowed."""
    query = """
    SELECT c.city, COUNT(c.customer_id) AS total_customers
    FROM customers c
    GROUP BY c.city
    ORDER BY total_customers DESC;
    """
    is_valid, reason = validate_sql(query)
    assert is_valid is True
    assert reason == ""


def test_valid_cte_query():
    """Common Table Expressions (WITH ... SELECT) must be allowed."""
    query = """
    WITH customer_spending AS (
        SELECT customer_id, SUM(total_amount) AS spent
        FROM orders
        GROUP BY customer_id
    )
    SELECT * FROM customer_spending WHERE spent > 5000;
    """
    is_valid, reason = validate_sql(query)
    assert is_valid is True
    assert reason == ""


def test_block_drop_table():
    """DROP TABLE statements must be blocked."""
    query = "DROP TABLE customers;"
    is_valid, reason = validate_sql(query)
    assert is_valid is False
    assert "Forbidden keyword" in reason or "Only SELECT" in reason
    assert is_safe_sql(query) is False


def test_block_delete_from():
    """DELETE FROM statements must be blocked."""
    query = "DELETE FROM orders WHERE customer_id = 1;"
    is_valid, reason = validate_sql(query)
    assert is_valid is False
    assert is_safe_sql(query) is False


def test_block_update_statement():
    """UPDATE statements must be blocked."""
    query = "UPDATE products SET price = 0 WHERE product_id = 1;"
    is_valid, reason = validate_sql(query)
    assert is_valid is False
    assert is_safe_sql(query) is False


def test_block_insert_into():
    """INSERT INTO statements must be blocked."""
    query = "INSERT INTO customers (name, email, city) VALUES ('Hacker', 'h@x.com', 'Nowhere');"
    is_valid, reason = validate_sql(query)
    assert is_valid is False
    assert is_safe_sql(query) is False


def test_block_truncate_table():
    """TRUNCATE statements must be blocked."""
    query = "TRUNCATE TABLE order_items;"
    is_valid, reason = validate_sql(query)
    assert is_valid is False
    assert is_safe_sql(query) is False


def test_block_alter_table():
    """ALTER TABLE statements must be blocked."""
    query = "ALTER TABLE products DROP COLUMN price;"
    is_valid, reason = validate_sql(query)
    assert is_valid is False
    assert is_safe_sql(query) is False


def test_block_multi_statement_injection():
    """Multi-statement queries separated by semicolons must be blocked."""
    query = "SELECT * FROM customers; DROP TABLE orders;"
    is_valid, reason = validate_sql(query)
    assert is_valid is False
    assert "Multi-statement queries" in reason or "Forbidden keyword" in reason


def test_empty_or_whitespace_query():
    """Empty or whitespace-only queries must fail validation."""
    assert validate_sql("")[0] is False
    assert validate_sql("   \n\t  ")[0] is False
    assert validate_sql("-- just a comment")[0] is False
