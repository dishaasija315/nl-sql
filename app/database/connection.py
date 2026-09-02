"""
Database connection and query execution module.
Provides SQLAlchemy engine connection and safe execution helper with column metadata.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Union

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Project root
BASE_DIR = Path(__file__).resolve().parents[2]

# Load .env
load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env")

# PostgreSQL engine
engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def execute_query(query: str) -> Union[Dict[str, Any], str]:
    """
    Execute a SQL query and return columns, rows as dictionaries, and raw tuples.

    Returns:
        dict: {"columns": list[str], "rows": list[dict], "raw_rows": list[tuple]}
        str: "DATABASE_ERROR: <details>" if an error occurs.
    """
    try:
        with engine.connect() as connection:
            result = connection.execute(text(query))
            
            # Fetch column names
            columns = list(result.keys()) if result.returns_rows else []
            
            if result.returns_rows:
                raw_rows = result.fetchall()
                # Convert rows to list of dicts for JSON / DataFrame serialization
                dict_rows = [dict(zip(columns, row)) for row in raw_rows]
                return {
                    "columns": columns,
                    "rows": dict_rows,
                    "raw_rows": raw_rows,
                }
            return {
                "columns": [],
                "rows": [],
                "raw_rows": [],
            }

    except Exception as e:
        return f"DATABASE_ERROR: {str(e)}"


def test_connection() -> bool:
    """Test PostgreSQL connection and print confirmation."""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("Database connected successfully!")
            print(f"Test query result: {result.fetchone()}")
            return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False


if __name__ == "__main__":
    test_connection()