"""
SQL Safety Validator Module.
Ensures that generated queries are read-only (SELECT / WITH ... SELECT),
blocks destructive DDL/DML statements, and prevents multi-statement injection.

NOTE: Keyword-based validation provides a helpful baseline safety filter.
For production security, use restricted database user privileges (read-only roles).
"""

import re
from typing import Tuple

# Disallowed SQL keywords that could modify state, schema, or permissions
FORBIDDEN_KEYWORDS = [
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "GRANT",
    "REVOKE",
    "EXEC",
    "EXECUTE",
    "REPLACE",
    "MERGE",
    "UPSERT",
    "CALL",
    "VACUUM",
    "REINDEX",
    "SET",
    "COMMENT",
]


def validate_sql(query: str) -> Tuple[bool, str]:
    """
    Validate SQL query to ensure it is a safe read-only SELECT query.

    Returns:
        (is_valid, error_message): Tuple where is_valid is True if safe, False otherwise.
    """
    if not query or not query.strip():
        return False, "Query is empty."

    cleaned = query.strip()

    if cleaned == "REJECTED_NON_SELECT_INTENT":
        return False, "Data modification commands (DELETE, DROP, UPDATE, INSERT, ALTER) are strictly prohibited."

    # Remove single line comments (-- ...) and multi-line comments (/* ... */)
    cleaned_no_comments = re.sub(r"--.*$", "", cleaned, flags=re.MULTILINE)
    cleaned_no_comments = re.sub(r"/\*.*?\*/", "", cleaned_no_comments, flags=re.DOTALL).strip()

    if not cleaned_no_comments:
        return False, "Query contains only comments or whitespace."

    upper_query = cleaned_no_comments.upper()

    # Must start with SELECT or WITH (common table expressions)
    if not (upper_query.startswith("SELECT") or upper_query.startswith("WITH")):
        return False, "Only SELECT or WITH ... SELECT queries are permitted."

    # Prevent multi-statement attacks (e.g., 'SELECT 1; DROP TABLE orders')
    # A single trailing semicolon is allowed, but interior semicolons are rejected.
    statements = [s.strip() for s in cleaned_no_comments.split(";") if s.strip()]
    if len(statements) > 1:
        return False, "Multi-statement queries separated by semicolons are not allowed."

    # Check for forbidden keywords as isolated word boundaries
    for keyword in FORBIDDEN_KEYWORDS:
        pattern = rf"\b{keyword}\b"
        if re.search(pattern, upper_query):
            return False, f"Forbidden keyword detected: '{keyword}'. Only read-only SELECT queries are allowed."

    return True, ""


def is_safe_sql(query: str) -> bool:
    """Helper returning boolean for quick conditional checks."""
    is_valid, _ = validate_sql(query)
    return is_valid