"""
Unit and integration tests for LangGraph agent workflow with mocked LLM calls.
Verifies the self-correcting retry loop, validation gates, and execution routing.
"""

from unittest.mock import patch
from app.agent.graph import run_agent


def test_agent_happy_path(mocker):
    """Test 1-shot successful flow: generate SQL -> validate -> execute -> answer."""
    mock_gen = mocker.patch(
        "app.agent.graph.generate_sql",
        return_value="SELECT city, COUNT(customer_id) AS total FROM customers GROUP BY city ORDER BY total DESC LIMIT 1;",
    )
    mock_ans = mocker.patch(
        "app.agent.graph.generate_final_answer",
        return_value="Delhi has the highest customer count with 2 customers.",
    )

    result = run_agent("Which city has the most customers?")

    assert mock_gen.called
    assert mock_ans.called
    assert result.get("error") == ""
    assert result.get("retry_count") == 0
    assert len(result.get("rows", [])) == 1
    assert "Delhi" in result.get("answer")


def test_agent_validation_retry_loop(mocker):
    """Test self-correction when LLM first generates invalid SQL (e.g., DROP TABLE), then fixes it."""
    # First call generates unsafe query, fix_sql generates safe query
    mock_gen = mocker.patch(
        "app.agent.graph.generate_sql",
        return_value="DROP TABLE customers;",
    )
    mock_fix = mocker.patch(
        "app.agent.graph.fix_sql",
        return_value="SELECT name, city FROM customers;",
    )
    mock_ans = mocker.patch(
        "app.agent.graph.generate_final_answer",
        return_value="Here is the list of customers and cities.",
    )

    result = run_agent("List all customers", max_retries=2)

    assert mock_gen.called
    assert mock_fix.called
    assert result.get("retry_count") == 1
    assert len(result.get("rows", [])) > 0
    assert result.get("answer") == "Here is the list of customers and cities."


def test_agent_db_error_retry_loop(mocker):
    """Test self-correction when generated SQL references a wrong column name causing a PostgreSQL error."""
    # First query references invalid column name 'unknown_col'
    mock_gen = mocker.patch(
        "app.agent.graph.generate_sql",
        return_value="SELECT unknown_col FROM customers;",
    )
    mock_fix = mocker.patch(
        "app.agent.graph.fix_sql",
        return_value="SELECT name FROM customers;",
    )
    mock_ans = mocker.patch(
        "app.agent.graph.generate_final_answer",
        return_value="All customer names retrieved successfully.",
    )

    result = run_agent("Get customer names", max_retries=2)

    assert mock_gen.called
    assert mock_fix.called
    assert result.get("retry_count") == 1
    assert len(result.get("rows", [])) > 0
    assert result.get("answer") == "All customer names retrieved successfully."


def test_agent_max_retries_exceeded(mocker):
    """Test termination when queries repeatedly fail and exceed max retries."""
    mock_gen = mocker.patch(
        "app.agent.graph.generate_sql",
        return_value="SELECT bad_col_1 FROM customers;",
    )
    mock_fix = mocker.patch(
        "app.agent.graph.fix_sql",
        return_value="SELECT bad_col_2 FROM customers;",
    )

    result = run_agent("Broken question", max_retries=2)

    assert result.get("retry_count") == 2
    assert "DATABASE_ERROR:" in result.get("error")
    assert result.get("answer") == ""
