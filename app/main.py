"""
FastAPI application entry point.
Initializes FastAPI, sets up CORS middleware, and includes API routers.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router

app = FastAPI(
    title="NL-to-SQL Business Analyst Agent API",
    description="Conversational AI agent that converts natural language business questions into PostgreSQL queries, executes them safely, and delivers executive summaries.",
    version="1.0.0",
)

# Enable CORS for Streamlit and other client interfaces
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include agent endpoints
app.include_router(router)


@app.get("/", summary="Root status")
async def root():
    return {
        "message": "NL-to-SQL Business Analyst API is running.",
        "docs_url": "/docs",
        "health_url": "/health",
    }
