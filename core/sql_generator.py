"""
SQL Generator
LangChain pipeline: Natural Language → SQL → Execution → NL Answer.

Supports both Anthropic Claude (claude-sonnet-4-20250514)
and OpenAI GPT-4o depending on which API key is present.
"""

from __future__ import annotations
import os
import re
import json
import textwrap
import pandas as pd

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from backend.db_loader import run_query, list_tables
from backend.rag_engine import get_rag_engine

# ── LLM Selection ──────────────────────────────────────────────────────────────
def _build_llm():
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    openai_key    = os.getenv("OPENAI_API_KEY", "")

    if anthropic_key:
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model="claude-sonnet-4-20250514",
            anthropic_api_key=anthropic_key,
            temperature=0,
            max_tokens=1024,
        )
    elif openai_key:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model="gpt-4o",
            openai_api_key=openai_key,
            temperature=0,
        )
    else:
        raise EnvironmentError(
            "No LLM API key found.\n"
            "Set ANTHROPIC_API_KEY or OPENAI_API_KEY in your .env file."
        )


# ── Prompt Templates ───────────────────────────────────────────────────────────
SQL_SYSTEM = """You are AnalytIQ, an expert data analyst assistant for a campus food-service
and e-commerce/SaaS business. You translate natural language business questions into
precise DuckDB SQL queries.

DATABASE CONTEXT (retrieved by semantic search):
{schema_context}

AVAILABLE TABLES: {table_list}

RULES:
1. Return ONLY valid DuckDB SQL — no explanation, no markdown fences, no backticks.
2. Use table and column names exactly as defined in the schema above.
3. Always include a LIMIT clause (default 100, or 10 for aggregations).
4. Use date filters with string comparison: WHERE date >= '2024-01-01'.
5. For "last week" → last 7 days from max(date) in the table.
6. For "this year" → 2024.
7. When joining with academic_calendar, join ON table.date = academic_calendar.date.
8. Never use subqueries when a WITH clause (CTE) is clearer.
9. If the question is ambiguous, make the most useful reasonable assumption.
10. Prefer readable column aliases over raw column names in SELECT.
"""

SQL_HUMAN = "Question: {question}"

ANSWER_SYSTEM = """You are AnalytIQ, a concise business analyst. 
Given a SQL query result, write a 2-4 sentence plain-English insight 
that directly answers the user's question. 
Focus on the most important numbers and business implications.
Do not repeat the question. Do not mention SQL.
"""

ANSWER_HUMAN = """User question: {question}

Query result (top rows):
{result_preview}

Write a concise business insight:"""

ERROR_RECOVERY_SYSTEM = """You are a DuckDB SQL expert. 
The following SQL query produced an error. Fix it and return ONLY the corrected SQL.
No explanation, no markdown.

Original SQL:
{original_sql}

Error:
{error}

Schema context:
{schema_context}
"""


# ── Core Pipeline ──────────────────────────────────────────────────────────────
class SQLGenerator:
    def __init__(self):
        self._llm          = _build_llm()
        self._str_parser   = StrOutputParser()
        self._rag          = get_rag_engine()
        self._sql_prompt   = ChatPromptTemplate.from_messages([
            ("system", SQL_SYSTEM),
            ("human",  SQL_HUMAN),
        ])
        self._ans_prompt   = ChatPromptTemplate.from_messages([
            ("system", ANSWER_SYSTEM),
            ("human",  ANSWER_HUMAN),
        ])
        self._fix_prompt   = ChatPromptTemplate.from_messages([
            ("system", ERROR_RECOVERY_SYSTEM),
        ])

    # ── Step 1: NL → SQL ───────────────────────────────────────────────────────
    def generate_sql(self, question: str) -> tuple[str, str]:
        """Returns (sql, schema_context_used)."""
        context = self._rag.retrieve(question, top_k=4)
        chain   = self._sql_prompt | self._llm | self._str_parser
        sql     = chain.invoke({
            "question":       question,
            "schema_context": context,
            "table_list":     ", ".join(list_tables()),
        })
        return _clean_sql(sql), context

    # ── Step 2: Execute with auto-retry ───────────────────────────────────────
    def execute_sql(self, sql: str, schema_context: str) -> tuple[pd.DataFrame, str, str]:
        """
        Returns (dataframe, final_sql, error).
        Attempts one auto-fix pass on failure.
        """
        df, err = run_query(sql)
        if err:
            fixed_sql = self._fix_sql(sql, err, schema_context)
            df, err   = run_query(fixed_sql)
            return df, fixed_sql, err
        return df, sql, ""

    def _fix_sql(self, original_sql: str, error: str, schema_context: str) -> str:
        chain  = self._fix_prompt | self._llm | self._str_parser
        result = chain.invoke({
            "original_sql":   original_sql,
            "error":          error,
            "schema_context": schema_context,
        })
        return _clean_sql(result)

    # ── Step 3: Results → NL Answer ───────────────────────────────────────────
    def generate_answer(self, question: str, df: pd.DataFrame) -> str:
        if df.empty:
            return "The query returned no results. Try rephrasing or broadening the question."
        preview = df.head(10).to_string(index=False)
        chain   = self._ans_prompt | self._llm | self._str_parser
        return chain.invoke({"question": question, "result_preview": preview})

    # ── Full Pipeline ─────────────────────────────────────────────────────────
    def query(self, question: str) -> dict:
        """
        End-to-end: question → SQL → execution → NL answer.

        Returns:
            {
              "question":       str,
              "sql":            str,
              "dataframe":      pd.DataFrame,
              "answer":         str,
              "error":          str,       # empty on success
              "schema_context": str,
            }
        """
        sql, schema_context = self.generate_sql(question)
        df, final_sql, error = self.execute_sql(sql, schema_context)

        answer = ""
        if not error and not df.empty:
            answer = self.generate_answer(question, df)
        elif error:
            answer = f"I couldn't execute that query. Error: {error}"

        return {
            "question":       question,
            "sql":            final_sql,
            "dataframe":      df,
            "answer":         answer,
            "error":          error,
            "schema_context": schema_context,
        }


# ── Helpers ────────────────────────────────────────────────────────────────────
def _clean_sql(raw: str) -> str:
    """Strip markdown fences, leading/trailing whitespace."""
    raw = raw.strip()
    # Remove ```sql ... ``` or ``` ... ```
    raw = re.sub(r"^```(?:sql)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


# ── Singleton ─────────────────────────────────────────────────────────────────
_generator: SQLGenerator | None = None

def get_sql_generator() -> SQLGenerator:
    global _generator
    if _generator is None:
        _generator = SQLGenerator()
    return _generator
