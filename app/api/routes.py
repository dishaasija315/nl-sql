"""
FastAPI route endpoints for the NL-to-SQL Business Analyst service.
"""

from fastapi import APIRouter, HTTPException, status
from app.models.schemas import AskRequest, AskResponse, HealthResponse, SchemaResponse
from app.agent.graph import run_agent
from app.database.schema import get_database_schema, inspect_schema
from app.database.connection import test_connection

router = APIRouter(tags=["NL-to-SQL Agent"])


@router.post(
    "/ask",
    response_model=AskResponse,
    summary="Ask a natural-language business question",
    description="Processes the business question through LangGraph: generates SQL, validates, executes in PostgreSQL, fixes if needed, and returns synthesized answer.",
)
async def ask_question(request: AskRequest) -> AskResponse:
    """Execute question through the LangGraph NL-to-SQL pipeline."""
    try:
        result = run_agent(
            question=request.question,
            max_retries=request.max_retries or 2,
        )
        
        return AskResponse(
            question=result.get("question", request.question),
            sql=result.get("sql_query", ""),
            columns=result.get("columns", []),
            rows=result.get("rows", []),
            answer=result.get("answer", "") or "No answer could be generated.",
            error=result.get("error") or None,
            retry_count=result.get("retry_count", 0),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing agent pipeline: {str(e)}",
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service and Database Health Check",
)
async def health_check() -> HealthResponse:
    """Check if the backend and PostgreSQL connection are operational."""
    db_ok = test_connection()
    tables_dict = inspect_schema() if db_ok else {}
    
    return HealthResponse(
        status="healthy" if db_ok else "degraded",
        database="connected" if db_ok else "disconnected",
        tables_count=len(tables_dict),
    )


@router.get(
    "/schema",
    response_model=SchemaResponse,
    summary="Get Database Schema",
    description="Returns current PostgreSQL tables, column types, and foreign key relationships.",
)
async def get_schema() -> SchemaResponse:
    """Retrieve active database schema representation."""
    schema_text = get_database_schema(force_refresh=True)
    tables = inspect_schema()
    return SchemaResponse(
        schema_text=schema_text,
        tables=tables,
    )
