"""
LangGraph State Definition for the NL-to-SQL Business Analyst Agent.
"""

from typing import Any, Dict, List, Tuple, TypedDict


class SQLAgentState(TypedDict):
    """
    Represents the complete state of the SQL Agent workflow.
    """
    question: str                  # Original user question
    schema: str                    # Dynamic DB schema string
    sql_query: str                 # Generated or fixed SQL query
    columns: List[str]             # Query result column names
    rows: List[Dict[str, Any]]     # Query result rows as list of dicts
    raw_rows: List[Tuple[Any, ...]] # Query result raw tuples
    result_str: str                # String representation of results for LLM
    error: str                     # Validation or database execution error message
    answer: str                    # Final business answer
    retry_count: int               # Current retry attempt counter
    max_retries: int               # Maximum allowed retries before terminating
    is_security_violation: bool    # True if query was blocked for safety/modification attempt

