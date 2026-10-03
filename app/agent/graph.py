"""
LangGraph Workflow Definition for NL-to-SQL Business Analyst Agent.
Implements the multi-step cycle:
  get_schema -> generate_sql -> validate_sql -> execute_sql (with fix_sql retry loop) -> generate_answer
"""

from typing import Any, Dict
from langgraph.graph import StateGraph, START, END

from app.database.schema import get_database_schema
from app.database.validator import validate_sql
from app.database.connection import execute_query
from app.llm.gemini import (
    generate_sql,
    fix_sql,
    generate_final_answer,
)
from app.agent.state import SQLAgentState


# ---------------------------------------------------------------------------
# Node Implementations
# ---------------------------------------------------------------------------

def get_schema_node(state: SQLAgentState) -> Dict[str, Any]:
    """Inspect and load live PostgreSQL schema if not already present."""
    if not state.get("schema"):
        schema = get_database_schema()
        return {"schema": schema}
    return {}


def generate_sql_node(state: SQLAgentState) -> Dict[str, Any]:
    """Generate initial PostgreSQL query using Gemini and schema."""
    print(f"\n[Agent] Generating SQL for question: '{state['question']}'...")
    sql_query = generate_sql(
        question=state["question"],
        schema=state.get("schema", ""),
    )
    print(f"[Agent] Generated SQL:\n  {sql_query}")
    return {
        "sql_query": sql_query,
        "error": "",
    }


def validate_sql_node(state: SQLAgentState) -> Dict[str, Any]:
    """Validate SQL query for safety (SELECT only, no DDL/DML, no multi-statements)."""
    sql_query = state.get("sql_query", "")
    is_valid, reason = validate_sql(sql_query)
    
    if not is_valid:
        print(f"[Agent] Validation Failed: {reason}")
        security_answer = (
            "I am a read-only Business Analyst AI. For security and database integrity reasons, "
            "data modification commands (such as DELETE, DROP, UPDATE, INSERT, ALTER) are strictly prohibited. "
            "I can only retrieve and analyze data using read-only SELECT queries."
        )
        return {
            "error": f"SQL Safety Validation Failed: {reason}",
            "answer": security_answer,
            "is_security_violation": True,
        }
    
    print("[Agent] SQL Validation Passed.")
    return {"error": "", "is_security_violation": False}


def execute_sql_node(state: SQLAgentState) -> Dict[str, Any]:
    """Execute validated query against PostgreSQL database."""
    sql_query = state.get("sql_query", "")
    print(f"[Agent] Executing SQL Query on PostgreSQL...")
    
    result = execute_query(sql_query)
    
    # Check for database execution errors
    if isinstance(result, str) and result.startswith("DATABASE_ERROR:"):
        print(f"[Agent] Database Execution Error: {result}")
        return {
            "columns": [],
            "rows": [],
            "raw_rows": [],
            "result_str": "",
            "error": result,
        }
    
    # Successful query
    columns = result.get("columns", [])
    rows = result.get("rows", [])
    raw_rows = result.get("raw_rows", [])
    
    # Format a clean string representation for the LLM
    if not rows:
        result_str = "Query executed successfully. 0 rows returned."
    else:
        # Include column headers and data rows
        row_lines = [", ".join(f"{k}: {v}" for k, v in r.items()) for r in rows]
        result_str = f"Columns: {columns}\nData:\n" + "\n".join(row_lines)
    
    print(f"[Agent] Query Succeeded. {len(rows)} row(s) retrieved.")
    return {
        "columns": columns,
        "rows": rows,
        "raw_rows": raw_rows,
        "result_str": result_str,
        "error": "",
    }


def fix_sql_node(state: SQLAgentState) -> Dict[str, Any]:
    """Send failed SQL, error message, and schema to Gemini for correction."""
    current_retry = state.get("retry_count", 0) + 1
    print(f"\n[Agent] Attempting SQL fix (Retry {current_retry}/{state.get('max_retries', 2)})...")
    print(f"[Agent] Error to resolve: {state.get('error')}")
    
    corrected_sql = fix_sql(
        question=state["question"],
        bad_sql=state.get("sql_query", ""),
        error=state.get("error", ""),
        schema=state.get("schema", ""),
    )
    
    print(f"[Agent] Corrected SQL:\n  {corrected_sql}")
    return {
        "sql_query": corrected_sql,
        "error": "",
        "retry_count": current_retry,
    }


def generate_answer_node(state: SQLAgentState) -> Dict[str, Any]:
    """Synthesize final business answer for user."""
    print("[Agent] Synthesizing final business answer...")
    answer = generate_final_answer(
        question=state["question"],
        sql_query=state.get("sql_query", ""),
        result=state.get("result_str", ""),
    )
    return {"answer": answer}


# ---------------------------------------------------------------------------
# Conditional Edge Routing
# ---------------------------------------------------------------------------

def decide_after_validation(state: SQLAgentState) -> str:
    """Route to execute if valid, or fix_sql if invalid within retry limit (unless security violation)."""
    if not state.get("error"):
        return "execute_sql"
    
    if state.get("is_security_violation"):
        return "end"
    
    max_retries = state.get("max_retries", 2)
    if state.get("retry_count", 0) < max_retries:
        return "fix_sql"
    
    return "end"


def decide_after_execution(state: SQLAgentState) -> str:
    """Route to generate_answer if successful, or fix_sql on database error."""
    if not state.get("error"):
        return "generate_answer"
    
    max_retries = state.get("max_retries", 2)
    if state.get("retry_count", 0) < max_retries:
        return "fix_sql"
    
    return "end"


# ---------------------------------------------------------------------------
# LangGraph Graph Assembly
# ---------------------------------------------------------------------------

graph_builder = StateGraph(SQLAgentState)

# Add Nodes
graph_builder.add_node("get_schema", get_schema_node)
graph_builder.add_node("generate_sql", generate_sql_node)
graph_builder.add_node("validate_sql", validate_sql_node)
graph_builder.add_node("execute_sql", execute_sql_node)
graph_builder.add_node("fix_sql", fix_sql_node)
graph_builder.add_node("generate_answer", generate_answer_node)

# Flow Edges
graph_builder.add_edge(START, "get_schema")
graph_builder.add_edge("get_schema", "generate_sql")
graph_builder.add_edge("generate_sql", "validate_sql")

# Validate -> Execute OR Fix SQL OR END
graph_builder.add_conditional_edges(
    "validate_sql",
    decide_after_validation,
    {
        "execute_sql": "execute_sql",
        "fix_sql": "fix_sql",
        "end": END,
    },
)

# Fix SQL -> Validate SQL (ensures fixed SQL is re-validated before execution)
graph_builder.add_edge("fix_sql", "validate_sql")

# Execute -> Answer OR Fix SQL OR END
graph_builder.add_conditional_edges(
    "execute_sql",
    decide_after_execution,
    {
        "generate_answer": "generate_answer",
        "fix_sql": "fix_sql",
        "end": END,
    },
)

# Answer -> END
graph_builder.add_edge("generate_answer", END)

# Compile Graph
graph = graph_builder.compile()


# ---------------------------------------------------------------------------
# High-Level Agent Runner Function
# ---------------------------------------------------------------------------

def run_agent(question: str, max_retries: int = 2) -> Dict[str, Any]:
    """
    Run the LangGraph NL-to-SQL Agent pipeline for a given user question.

    Args:
        question: Natural language business question.
        max_retries: Maximum number of correction attempts for invalid/failing SQL.

    Returns:
        dict: Full state including answer, sql_query, columns, rows, error, retry_count.
    """
    initial_state: SQLAgentState = {
        "question": question,
        "schema": "",
        "sql_query": "",
        "columns": [],
        "rows": [],
        "raw_rows": [],
        "result_str": "",
        "error": "",
        "answer": "",
        "retry_count": 0,
        "max_retries": max_retries,
    }
    
    return graph.invoke(initial_state)


# ---------------------------------------------------------------------------
# Interactive CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("NL-to-SQL Business Analyst Agent (CLI)")
    print("=" * 60)
    
    user_input = input("\nAsk a business question (or type 'quit' to exit): ").strip()
    
    if user_input and user_input.lower() != "quit":
        result = run_agent(user_input)
        
        print("\n" + "=" * 60)
        print("RESULT SUMMARY")
        print("=" * 60)
        print(f"Generated SQL: {result.get('sql_query')}")
        print(f"Columns: {result.get('columns')}")
        print(f"Rows Count: {len(result.get('rows', []))}")
        
        if result.get("answer"):
            print(f"\nFinal Answer:\n{result.get('answer')}")
        elif result.get("error"):
            print(f"\nCould not answer question due to error:\n{result.get('error')}")
            
        print("=" * 60)