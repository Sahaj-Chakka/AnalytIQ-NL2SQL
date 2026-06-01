"""
AnalytIQ — Streamlit Frontend
Natural Language BI Assistant
Run: streamlit run frontend/app.py
"""

import os
import sys
import json
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime

# ── Path fix so imports resolve when run from repo root ──────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AnalytIQ",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── API Config ───────────────────────────────────────────────────────────────
API_URL = os.getenv("ANALYTIQ_API_URL", "http://localhost:8000")

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Main background */
    .stApp { background-color: #0f1117; }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #161b27;
        border-right: 1px solid #1e293b;
    }

    /* Chat bubbles */
    .user-bubble {
        background: linear-gradient(135deg, #1d4ed8, #7c3aed);
        color: white;
        padding: 12px 16px;
        border-radius: 16px 16px 4px 16px;
        margin: 8px 0;
        max-width: 80%;
        margin-left: auto;
        font-size: 14px;
    }
    .assistant-bubble {
        background: #1e293b;
        color: #e2e8f0;
        padding: 14px 18px;
        border-radius: 4px 16px 16px 16px;
        margin: 8px 0;
        max-width: 90%;
        font-size: 14px;
        border-left: 3px solid #3b82f6;
    }
    .insight-text {
        font-size: 15px;
        line-height: 1.7;
        color: #cbd5e1;
    }

    /* SQL code block */
    .sql-block {
        background: #0d1117;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 12px 16px;
        font-family: 'DM Mono', monospace;
        font-size: 12px;
        color: #7dd3fc;
        margin-top: 8px;
        white-space: pre-wrap;
    }

    /* Metric cards */
    .metric-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 14px;
        text-align: center;
    }

    /* Suggestion chips */
    .suggestion-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
        margin-top: 12px;
    }

    /* Header */
    .analytiq-header {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 0 20px 0;
        border-bottom: 1px solid #1e293b;
        margin-bottom: 20px;
    }
    .analytiq-title {
        font-size: 22px;
        font-weight: 800;
        background: linear-gradient(135deg, #60a5fa, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .analytiq-subtitle {
        font-size: 11px;
        color: #475569;
        letter-spacing: 1.5px;
        text-transform: uppercase;
    }

    /* Hide default streamlit branding */
    #MainMenu, footer { visibility: hidden; }
    .stDeployButton { display: none; }
</style>
""", unsafe_allow_html=True)


# ── Session State ─────────────────────────────────────────────────────────────
if "messages"      not in st.session_state: st.session_state.messages      = []
if "query_history" not in st.session_state: st.session_state.query_history = []
if "show_sql"      not in st.session_state: st.session_state.show_sql      = True
if "auto_chart"    not in st.session_state: st.session_state.auto_chart    = True


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    st.session_state.show_sql   = st.toggle("Show generated SQL",   value=True)
    st.session_state.auto_chart = st.toggle("Auto-generate charts", value=True)

    st.divider()
    st.markdown("### 📋 Query History")
    if st.session_state.query_history:
        for i, q in enumerate(reversed(st.session_state.query_history[-10:])):
            if st.button(f"↩ {q[:48]}…" if len(q) > 48 else f"↩ {q}", key=f"hist_{i}"):
                st.session_state.prefill = q
    else:
        st.caption("No queries yet.")

    st.divider()
    st.markdown("### 📦 Data Sources")
    tables = ["academic_calendar","sales_transactions","inventory_levels",
              "forecast_vs_actual","supplier_orders","orders","subscriptions"]
    for t in tables:
        st.markdown(f"<small>• {t}</small>", unsafe_allow_html=True)

    st.divider()
    if st.button("🗑 Clear Chat"):
        st.session_state.messages = []
        st.session_state.query_history = []
        st.rerun()


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="analytiq-header">
  <span style="font-size:28px">📊</span>
  <div>
    <div class="analytiq-title">AnalytIQ</div>
    <div class="analytiq-subtitle">Natural Language BI Assistant</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ── Suggested Questions ───────────────────────────────────────────────────────
SUGGESTIONS = [
    "Which outlet had the highest revenue last week?",
    "Which SKUs are at stockout risk right now?",
    "What is Sysco's on-time delivery rate?",
    "Show me MRR growth month over month.",
    "How did sales differ on exam days vs normal days?",
    "Which customer segment has the highest churn rate?",
    "Show forecast accuracy by outlet for Fall semester.",
    "What campus events drove the biggest sales spikes?",
]

if not st.session_state.messages:
    st.markdown("**Ask a business question in plain English:**")
    cols = st.columns(2)
    for i, suggestion in enumerate(SUGGESTIONS):
        with cols[i % 2]:
            if st.button(suggestion, key=f"sug_{i}", use_container_width=True):
                st.session_state.prefill = suggestion


# ── Chat History Display ──────────────────────────────────────────────────────
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f'<div class="user-bubble">💬 {msg["content"]}</div>', unsafe_allow_html=True)
    else:
        with st.container():
            data = msg.get("data", {})

            # Insight text
            if data.get("answer"):
                st.markdown(
                    f'<div class="assistant-bubble"><div class="insight-text">{data["answer"]}</div></div>',
                    unsafe_allow_html=True
                )

            # SQL block
            if st.session_state.show_sql and data.get("sql"):
                with st.expander("🔍 Generated SQL", expanded=False):
                    st.code(data["sql"], language="sql")

            # Results table
            if data.get("rows"):
                df = pd.DataFrame(data["rows"])
                st.dataframe(df, use_container_width=True, hide_index=True)

                # Auto chart
                if st.session_state.auto_chart and len(df) > 1:
                    _render_chart(df, data.get("question", ""))

            # Error
            if data.get("error"):
                st.error(f"⚠️ {data['error']}")


# ── Chart Renderer ────────────────────────────────────────────────────────────
def _render_chart(df: pd.DataFrame, question: str):
    """Heuristically pick a chart type from the result shape."""
    cols      = list(df.columns)
    num_cols  = df.select_dtypes(include="number").columns.tolist()
    cat_cols  = df.select_dtypes(exclude="number").columns.tolist()

    if not num_cols:
        return

    CHART_COLORS = ["#3b82f6","#8b5cf6","#10b981","#f59e0b","#ef4444","#06b6d4","#ec4899"]

    try:
        # Time series: if there's a date column
        date_col = next((c for c in cat_cols if "date" in c.lower()), None)
        if date_col and num_cols:
            y_col = num_cols[0]
            color_col = next((c for c in cat_cols if c != date_col), None)
            fig = px.line(
                df, x=date_col, y=y_col, color=color_col,
                color_discrete_sequence=CHART_COLORS,
                template="plotly_dark",
            )
        # Bar: categorical + numeric
        elif cat_cols and num_cols and len(df) <= 30:
            x_col = cat_cols[0]
            y_col = num_cols[0]
            color_col = cat_cols[1] if len(cat_cols) > 1 else None
            fig = px.bar(
                df.sort_values(y_col, ascending=False),
                x=x_col, y=y_col, color=color_col,
                color_discrete_sequence=CHART_COLORS,
                template="plotly_dark",
            )
        # Pure numeric: histogram of first column
        elif num_cols:
            fig = px.histogram(
                df, x=num_cols[0],
                color_discrete_sequence=CHART_COLORS,
                template="plotly_dark",
            )
        else:
            return

        fig.update_layout(
            paper_bgcolor="#0f1117",
            plot_bgcolor="#0f1117",
            font_color="#94a3b8",
            margin=dict(l=20, r=20, t=30, b=20),
            height=350,
        )
        st.plotly_chart(fig, use_container_width=True)

    except Exception:
        pass   # Chart is best-effort; never crash the app over it


# ── Query Input ───────────────────────────────────────────────────────────────
st.divider()

prefill = st.session_state.pop("prefill", "") if "prefill" in st.session_state else ""

with st.form("query_form", clear_on_submit=True):
    col1, col2 = st.columns([6, 1])
    with col1:
        question = st.text_input(
            "Ask a question",
            value=prefill,
            placeholder="e.g. Which outlet had the highest overstock in October?",
            label_visibility="collapsed",
        )
    with col2:
        submitted = st.form_submit_button("Ask →", use_container_width=True)


# ── Query Execution ───────────────────────────────────────────────────────────
if submitted and question.strip():
    # Add user message
    st.session_state.messages.append({"role": "user", "content": question})
    st.session_state.query_history.append(question)

    with st.spinner("Thinking …"):
        try:
            resp = requests.post(
                f"{API_URL}/query",
                json={"question": question, "show_sql": st.session_state.show_sql},
                timeout=60,
            )
            if resp.status_code == 200:
                data = resp.json()
                data["question"] = question
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": data.get("answer", ""),
                    "data": data,
                })
            else:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "API error.",
                    "data": {"error": f"HTTP {resp.status_code}: {resp.text}", "question": question},
                })
        except requests.exceptions.ConnectionError:
            st.session_state.messages.append({
                "role": "assistant",
                "content": "",
                "data": {
                    "error": (
                        "Cannot connect to the AnalytIQ API. "
                        "Make sure the backend is running:\n\n"
                        "```bash\nuvicorn backend.main:app --reload\n```"
                    ),
                    "question": question,
                },
            })

    st.rerun()
