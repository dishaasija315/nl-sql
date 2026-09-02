"""
Gemini LLM integration using LangChain ChatGoogleGenerativeAI and LCEL chains.
Includes SQL generation, SQL error correction, and business answer synthesis.
"""

import os
import re
from typing import Any
from pathlib import Path
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser

from app.database.schema import get_database_schema
from app.llm.prompts import (
    SQL_GENERATION_PROMPT,
    SQL_FIX_PROMPT,
    ANSWER_SYNTHESIS_PROMPT,
)

# Project root
BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env")

# Initialize ChatGoogleGenerativeAI with low temperature for deterministic SQL generation
llm = ChatGoogleGenerativeAI(
    model=MODEL_NAME,
    google_api_key=GEMINI_API_KEY,
    temperature=0.0,
)

# LCEL Pipelines
sql_chain = SQL_GENERATION_PROMPT | llm | StrOutputParser()
fix_chain = SQL_FIX_PROMPT | llm | StrOutputParser()
answer_chain = ANSWER_SYNTHESIS_PROMPT | llm | StrOutputParser()


def clean_sql(sql_output: Any) -> str:
    """
    Remove markdown code fences, backticks, and extraneous whitespace from LLM SQL output.
    """
    if not sql_output:
        return ""
    
    # If list of content blocks returned, join text portions
    if isinstance(sql_output, list):
        text_parts = []
        for item in sql_output:
            if isinstance(item, dict) and "text" in item:
                text_parts.append(item["text"])
            elif isinstance(item, str):
                text_parts.append(item)
        sql = "\n".join(text_parts)
    else:
        sql = str(sql_output)
    
    # Remove markdown code fences like ```sql ... ``` or ``` ... ```
    cleaned = re.sub(r"```(?:sql)?\s*", "", sql, flags=re.IGNORECASE)
    cleaned = cleaned.replace("```", "").strip()
    
    # Strip any trailing semicolons or whitespace
    cleaned = cleaned.strip()
    return cleaned


def generate_sql(question: str, schema: str = "") -> str:
    """
    Generate a PostgreSQL SELECT query for a business question using dynamic schema.
    """
    if not schema:
        schema = get_database_schema()
        
    raw_sql = sql_chain.invoke({
        "schema": schema,
        "question": question,
    })
    
    return clean_sql(raw_sql)


def fix_sql(question: str, bad_sql: str, error: str, schema: str = "") -> str:
    """
    Generate a corrected PostgreSQL SELECT query given the error and failed query.
    """
    if not schema:
        schema = get_database_schema()
        
    corrected_raw = fix_chain.invoke({
        "schema": schema,
        "question": question,
        "bad_sql": bad_sql,
        "error": error,
    })
    
    return clean_sql(corrected_raw)


def generate_final_answer(question: str, sql_query: str, result: str) -> str:
    """
    Synthesize a clear, concise executive answer from query results.
    """
    raw_answer = answer_chain.invoke({
        "question": question,
        "sql_query": sql_query,
        "result": str(result),
    })
    
    if isinstance(raw_answer, list):
        text_parts = []
        for item in raw_answer:
            if isinstance(item, dict) and "text" in item:
                text_parts.append(item["text"])
            elif isinstance(item, str):
                text_parts.append(item)
        return "\n".join(text_parts).strip()
        
    return str(raw_answer).strip()


def ask_gemini(prompt: str) -> str:
    """Legacy helper for direct text prompts."""
    response = llm.invoke(prompt)
    return response.content.strip() if hasattr(response, "content") else str(response)