# 📊 AnalytIQ — Natural Language BI Assistant

> **Ask business questions in plain English. Get SQL, results, and insights — instantly.**

AnalytIQ is a RAG-powered Business Intelligence assistant that lets business users query operational, e-commerce, and SaaS data without writing a single line of SQL. Built on LangChain, Anthropic Claude (or OpenAI GPT-4o), ChromaDB, FastAPI, and Streamlit.

---

## 🎯 What It Does

```
User: "Which outlets had the highest overstock during exam week?"
         ↓
   RAG retrieves relevant table schemas from ChromaDB
         ↓
   LLM generates precise DuckDB SQL
         ↓
   Query executes against 7 real-world datasets
         ↓
   LLM writes a plain-English business insight
         ↓
   Streamlit renders results + auto-generated chart
```

---

## 🗂️ Datasets

All 7 datasets are grounded in real campus food-service operations (Compass Group) and extended with e-commerce + SaaS subscription data.

| Dataset | Rows | Description |
|---|---|---|
| `academic_calendar.csv` | 366 | Semester periods, exam weeks, holidays, campus events, promotions, traffic multiplier per day |
| `sales_transactions.csv` | ~57,000 | Item-level daily sales across 7 outlets (Dining Commons, Taco Bell, Starbucks, Panda Express, Einstein Bros, Micro Market, Fry Shack) |
| `inventory_levels.csv` | ~11,000 | Daily inventory health per outlet–category: on-hand, days-on-hand, overstock/stockout flags |
| `forecast_vs_actual.csv` | ~11,000 | Demand forecast vs actual with variance %, contextualized by academic calendar |
| `supplier_orders.csv` | ~1,100 | Sysco + 7 other suppliers: fill rates, on-time delivery, lead times, substitutions |
| `orders.csv` | ~3,400 | E-commerce orders by category, channel, customer segment, status |
| `subscriptions.csv` | ~923 | SaaS lifecycle events: new, upgrade, downgrade, churn, reactivation with MRR |

> **Note:** Raw CSVs are git-ignored. Run `python data/generate_data.py` once after cloning to generate them locally into `data/raw/`.

### Academic Calendar Dimensions

The `academic_calendar` table is the backbone of AnalytIQ's demand intelligence. Every sales, inventory, and forecast row can be joined to it to understand *why* demand shifted:

- **Weekday / Weekend** — food-service demand drops ~45% on weekends
- **Semester** — Spring, Summer (65% baseline), Fall, Break (30% baseline)
- **Exam Periods** — demand spikes 35% during finals weeks
- **Holidays** — 80% demand drop on major holidays
- **Campus Events** — 45% spike on Welcome Week, Homecoming, etc.
- **Promotions** — 20% uplift on 1st and 15th of each month

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        STREAMLIT UI                          │
│   Chat Interface · Query History · Plotly Charts             │
└────────────────────────┬─────────────────────────────────────┘
                         │ HTTP (REST)
┌────────────────────────▼─────────────────────────────────────┐
│                      FASTAPI BACKEND                         │
│   POST /query · GET /schema · GET /sample · GET /health      │
└──────┬───────────────────────────────────────┬───────────────┘
       │                                       │
┌──────▼──────────┐                   ┌────────▼──────────────┐
│   RAG ENGINE    │                   │    SQL GENERATOR      │
│                 │                   │                       │
│  ChromaDB       │  schema context   │  LangChain Chain      │
│  (schema        │ ──────────────►   │  Claude / GPT-4o      │
│   embeddings)   │                   │  NL → SQL → NL Answer │
└─────────────────┘                   └────────┬──────────────┘
                                               │ SQL
                                      ┌────────▼──────────────┐
                                      │     DUCKDB            │
                                      │  In-memory database   │
                                      │  7 CSV datasets       │
                                      └───────────────────────┘
```

### Tech Stack

| Layer | Technology |
|---|---|
| **Orchestration** | LangChain |
| **LLM** | Anthropic Claude (`claude-sonnet-4-20250514`) · OpenAI GPT-4o (fallback) |
| **Embeddings** | OpenAI `text-embedding-3-small` · `all-MiniLM-L6-v2` (local fallback) |
| **Vector Database** | ChromaDB (local persistent) · Pinecone-ready |
| **Query Engine** | DuckDB (in-memory, SQL over pandas DataFrames) |
| **Backend API** | FastAPI + Uvicorn |
| **Frontend** | Streamlit + Plotly |
| **Testing** | pytest |

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/Sahaj-Chakka/AnalytIQ-NL2SQL.git
cd AnalytIQ-NL2SQL
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env — add your ANTHROPIC_API_KEY or OPENAI_API_KEY
```

### 3. Generate Datasets

```bash
python data/generate_data.py
```

This creates all 7 CSVs in `data/raw/`. Takes ~10 seconds. Run this once after every fresh clone.

### 4. Start the API Backend

```bash
uvicorn app.main:app --reload
```

API available at `http://localhost:8000`. Swagger docs at `http://localhost:8000/docs`.

### 5. Start the Streamlit UI

```bash
streamlit run app/app.py
```

Open `http://localhost:8501` in your browser.

---

## 💬 Example Queries

**Inventory & Operations**
- *"Which outlets had the most overstock days in Q3?"*
- *"Which SKUs are at stockout risk right now?"*
- *"Show me waste quantity by category at Dining Commons."*

**Demand & Forecasting**
- *"How did sales compare on exam days vs normal days?"*
- *"Which outlet had the worst forecast accuracy in December?"*
- *"What campus events drove the biggest sales spikes?"*

**Supplier Performance**
- *"What is Sysco's on-time delivery rate for 2024?"*
- *"Which supplier has the lowest fill rate?"*
- *"Show me substitution frequency by supplier."*

**E-Commerce**
- *"What is the average order value by category?"*
- *"Which channel has the highest refund rate?"*
- *"Show me monthly revenue trend from e-commerce orders."*

**SaaS / Subscriptions**
- *"What is the churn rate by plan tier?"*
- *"Show me MRR growth month over month."*
- *"Which customer segment has the highest upgrade rate?"*

---

## 📁 Project Structure

```
AnalytIQ-NL2SQL/
│
├── app/                           # 🖥  UI Layer — visuals and API only
│   ├── app.py                     # Streamlit chat UI + Plotly charts
│   └── main.py                    # FastAPI REST API (POST /query, GET /schema …)
│
├── core/                          # 🧠 Brain Layer — all LLM & RAG logic
│   ├── __init__.py
│   ├── rag_engine.py              # ChromaDB vector store + schema retrieval
│   ├── sql_generator.py           # LangChain NL→SQL→NL pipeline
│   └── schema_registry.py        # Table schemas + semantic descriptions
│
├── data/                          # 💾 Data Layer — generation, loading, raw files
│   ├── generate_data.py           # Synthetic dataset generator (run once)
│   ├── db_loader.py               # DuckDB loader + query executor
│   └── raw/                       # Generated CSVs (git-ignored)
│       ├── academic_calendar.csv  # 366 rows — demand context backbone
│       ├── sales_transactions.csv # ~57K rows — outlet × SKU × day sales
│       ├── inventory_levels.csv   # ~11K rows — daily inventory health
│       ├── forecast_vs_actual.csv # ~11K rows — demand forecast accuracy
│       ├── supplier_orders.csv    # ~1.1K rows — procurement & delivery
│       ├── orders.csv             # ~3.4K rows — e-commerce transactions
│       └── subscriptions.csv      # ~923 rows — SaaS lifecycle events
│
├── tests/                         # ✅ Quality Layer
│   ├── __init__.py
│   └── test_pipeline.py           # 14 pytest tests (DB + schema registry)
│
├── conftest.py                    # pytest path config (auto-used)
├── .env.example                   # Environment variable template
├── .gitignore
├── requirements.txt
├── LICENSE
└── README.md
```

### Why This Structure

| Layer | Folder | Responsibility |
|---|---|---|
| UI | `app/` | Buttons, layout, charts, API endpoints — no business logic |
| Brain | `core/` | All LLM, RAG, and SQL generation |
| Data | `data/` | CSV generation, DuckDB loading, raw files |
| Quality | `tests/` | Isolated tests that don't need the UI running |

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

All 14 tests cover: table loading, row counts, column validation, multi-table joins, inventory status logic, supplier aggregations, SaaS churn queries, and exam-period demand spikes.

---

## 🔧 Configuration

### Switching LLMs

AnalytIQ auto-detects which LLM to use based on which API key is present in `.env`. It prefers Anthropic Claude when both keys exist.

```env
ANTHROPIC_API_KEY=sk-ant-...   # Uses claude-sonnet-4-20250514
OPENAI_API_KEY=sk-...          # Uses gpt-4o (fallback)
```

### Switching to Pinecone

To use Pinecone instead of ChromaDB, update `core/rag_engine.py`:

```python
import pinecone
from langchain_pinecone import PineconeVectorStore
```

Set in `.env`:
```env
PINECONE_API_KEY=your_key
PINECONE_ENV=us-east-1-aws
PINECONE_INDEX=analytiq-schemas
```

### API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/query` | Main NL→SQL→results endpoint |
| `GET` | `/tables` | List all available tables |
| `GET` | `/schema` | All table schema descriptions |
| `GET` | `/schema/{table}` | Schema for a specific table |
| `GET` | `/sample/{table}` | Sample rows from a table |
| `GET` | `/health` | Health check + vector store stats |
| `GET` | `/docs` | Interactive Swagger UI |

---

## 🛣️ Roadmap

- [ ] Pinecone cloud vector store integration
- [ ] Multi-turn conversational memory (LangChain `ConversationBufferMemory`)
- [ ] Chart type selector in UI (bar / line / scatter / heatmap)
- [ ] Export query results as CSV / Excel
- [ ] Scheduled report generation
- [ ] Slack / Teams bot integration
- [ ] PostgreSQL / Snowflake connector (replace DuckDB for production)

---

## 👤 Author

**Sahaj Chakka** — Data Analyst  
[GitHub](https://github.com/Sahaj-Chakka) · [AnalytIQ-NL2SQL](https://github.com/Sahaj-Chakka/AnalytIQ-NL2SQL)

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
