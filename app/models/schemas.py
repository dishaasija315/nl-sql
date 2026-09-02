"""
Pydantic schemas for API request and response data validation.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    """Request payload for NL-to-SQL business question endpoint."""
    question: str = Field(
        ...,
        min_length=3,
        description="Natural language question to translate into SQL and execute.",
        examples=["Which city has the most customers?"],
    )
    max_retries: Optional[int] = Field(
        default=2,
        ge=0,
        le=5,
        description="Maximum error-correction retry attempts.",
    )


class AskResponse(BaseModel):
    """Response payload containing generated SQL, query results, and business answer."""
    question: str
    sql: str
    columns: List[str] = Field(default_factory=list)
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    answer: str
    error: Optional[str] = None
    retry_count: int = 0


class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str
    database: str
    tables_count: int


class SchemaResponse(BaseModel):
    """Database schema inspection response."""
    schema_text: str
    tables: Dict[str, Any]
