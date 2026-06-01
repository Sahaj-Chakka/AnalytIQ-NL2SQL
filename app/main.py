"""
AnalytIQ FastAPI Backend
Endpoints:
  POST /query        — NL question → SQL + results + insight
  GET  /schema       — List all table schemas
  GET  /schema/{t}   — Schema for a specific table
  GET  /tables       — List available tables
  GET  /sample/{t}   — Sample rows from a table
  GET  /health       — Health check + vector store stats
"""

from __future__ import annotations
import os
from contextlib import asynccontextmanager
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.db_loader import get_connection, get_table_sample, list_tables
from backend.rag_engine import get_rag_engine
from backend.sql_generator import get_sql_generator
from backend.schema_registry import SCHEMA_REGISTRY, get_schema_text


# ── Lifespan: warm up DB + RAG on startup ─────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 AnalytIQ starting up …")
    print("  Loading database …")
    get_connection()
    print("  Loading RAG engine …")
    get_rag_engine()
    print("  Loading SQL generator …")
    get_sql_generator()
    print("✅  Ready.")
    yield
    print("🛑  Shutting down.")


app = FastAPI(
    title="AnalytIQ",
    description="Natural Language BI Assistant — RAG-powered SQL generation over campus operations + e-commerce + SaaS data.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response Models ─────────────────────────────────────────────────
class QueryRequest(BaseModel):
    question: str
    show_sql: bool = True

class QueryResponse(BaseModel):
    question:       str
    sql:            str
    answer:         str
    rows:           list[dict]
    columns:        list[str]
    row_count:      int
    error:          str
    schema_context: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.post("/query", response_model=QueryResponse)
async def query_endpoint(req: QueryRequest):
    """
    Main endpoint. Accepts a natural-language business question,
    returns SQL, result rows, and a plain-English insight.
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    gen    = get_sql_generator()
    result = gen.query(req.question)

    df: pd.DataFrame = result["dataframe"]
    rows    = df.to_dict(orient="records") if not df.empty else []
    columns = list(df.columns) if not df.empty else []

    return QueryResponse(
        question       = result["question"],
        sql            = result["sql"] if req.show_sql else "",
        answer         = result["answer"],
        rows           = rows,
        columns        = columns,
        row_count      = len(rows),
        error          = result["error"],
        schema_context = result["schema_context"] if req.show_sql else None,
    )


@app.get("/tables")
async def get_tables():
    """List all available tables."""
    return {"tables": list_tables()}


@app.get("/schema")
async def get_all_schemas():
    """Return all table schema descriptions."""
    return {
        table: {
            "description": schema["description"],
            "columns": schema["columns"],
            "sample_questions": schema["sample_questions"],
        }
        for table, schema in SCHEMA_REGISTRY.items()
    }


@app.get("/schema/{table_name}")
async def get_schema(table_name: str):
    """Return schema for a specific table."""
    if table_name not in SCHEMA_REGISTRY:
        raise HTTPException(
            status_code=404,
            detail=f"Table '{table_name}' not found. Available: {list_tables()}"
        )
    schema = SCHEMA_REGISTRY[table_name]
    return {
        "table":            table_name,
        "description":      schema["description"],
        "columns":          schema["columns"],
        "sample_questions": schema["sample_questions"],
        "formatted_text":   get_schema_text(table_name),
    }


@app.get("/sample/{table_name}")
async def get_sample(table_name: str, n: int = 5):
    """Return sample rows from a table."""
    if table_name not in list_tables():
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found.")
    df = get_table_sample(table_name, n=n)
    return {
        "table":   table_name,
        "rows":    df.to_dict(orient="records"),
        "columns": list(df.columns),
    }


@app.get("/health")
async def health():
    """Health check + system stats."""
    rag   = get_rag_engine()
    stats = rag.stats()
    return {
        "status":       "ok",
        "tables":       list_tables(),
        "vector_store": stats,
        "version":      "1.0.0",
    }
