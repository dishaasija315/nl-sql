# 📊 NL-to-SQL Business Analyst Agent

An enterprise-ready **Natural Language to SQL Business Analyst Agent** powered by **Google Gemini**, **LangChain**, **LangGraph**, and **PostgreSQL**.

This system allows business stakeholders to ask complex questions in plain English, autonomously generates and validates safe PostgreSQL queries using dynamic live schema introspection, self-corrects execution errors via an iterative feedback loop, and delivers executive-ready business answers accompanied by interactive Plotly visualizations.

---

## 🏗️ Architecture & Workflow

The agent uses a cyclic **LangGraph** state machine with validation safeguards and automated error correction:

```mermaid
graph TD
    Start([User Question]) --> GetSchema[Inspect Live Schema]
    GetSchema --> GenSQL[Generate SQL with Gemini]
    GenSQL --> ValidateSQL{Validate SQL Safety}
    
    ValidateSQL -->|Unsafe / Non-SELECT| FixSQL[Fix SQL with Error Context]
    ValidateSQL -->|Valid SELECT| ExecSQL[Execute in PostgreSQL]
    
    ExecSQL -->|Execution Error / Bad Column| FixSQL
    ExecSQL -->|Success| GenAnswer[Synthesize Business Answer]
    
    FixSQL -->|Retry < Max Retries| ValidateSQL
    FixSQL -->|Retries Exceeded| EndNode([Return Error])
    
    GenAnswer --> EndNodeSuccess([Return Answer + SQL + Visuals])
```

---

## 🌟 Key Features

1. **Dynamic PostgreSQL Schema Introspection**:
   - Introspects table definitions, column types, primary keys, and foreign keys directly from PostgreSQL using SQLAlchemy.
   - Adapts to schema changes without requiring hardcoded schema prompts.

2. **Safe SQL Generation & Validation**:
   - Strictly enforces read-only `SELECT` and `WITH ... SELECT` queries.
   - Proactively blocks destructive statements (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `TRUNCATE`, `ALTER`, `GRANT`, `REVOKE`).
   - Prevents semicolon-separated multi-statement injection.

3. **Self-Correcting LangGraph Loop**:
   - Catches PostgreSQL syntax/column errors and feeds the error trace back to Gemini with schema context to fix queries automatically (up to 2 bounded retries).

4. **Executive Business Synthesis**:
   - Translates raw database rows into polished, conversational business insights.

5. **Multi-Interface Support**:
   - **Interactive CLI**: Fast terminal interface.
   - **FastAPI REST Backend**: Production API endpoints (`/ask`, `/health`, `/schema`) running on port 8001 with interactive OpenAPI documentation.
   - **Streamlit Dashboard**: Modern UI with interactive data tables and automated Plotly visualizations (Bar charts for categories, Line charts for date/time trends).

6. **Comprehensive Unit & Mock Test Suite**:
   - Pytest suite (20 tests) verifying validator safety rules, database connections, and LangGraph retry workflows with mocked LLMs.

---

## 🛠️ Tech Stack

- **LLM**: Google Gemini (`ChatGoogleGenerativeAI` via `langchain-google-genai`)
- **Agent Orchestration**: LangChain & LangGraph
- **Database**: PostgreSQL 16 (via Docker)
- **ORM / Driver**: SQLAlchemy 2.0 + Psycopg 3
- **Backend API**: FastAPI + Uvicorn + Pydantic v2
- **Frontend Dashboard**: Streamlit + Plotly + Pandas
- **Testing**: Pytest + Pytest-Mock

---

## 📂 Project Structure

```
nl-sql-business-analyst/
│
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app entry point & CORS
│   │
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── state.py             # LangGraph state TypedDict
│   │   └── graph.py             # LangGraph agent graph, nodes, and CLI
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py            # API endpoints (/ask, /health, /schema)
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py        # SQLAlchemy engine & execution helper
│   │   ├── schema.py            # Dynamic PostgreSQL schema introspection
│   │   └── validator.py         # SQL safety & SELECT validation
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── gemini.py            # ChatGoogleGenerativeAI & LCEL chains
│   │   └── prompts.py           # ChatPromptTemplates for generation & fix
│   │
│   └── models/
│       ├── __init__.py
│       └── schemas.py           # Pydantic request/response schemas
│
├── data/
│   └── seed.sql                 # Sample PostgreSQL database tables & seed data
│
├── frontend/
│   └── streamlit_app.py         # Streamlit visual dashboard with Plotly charts
│
├── tests/
│   ├── __init__.py
│   ├── test_validator.py        # SQL validator security tests (11 tests)
│   ├── test_database.py         # Database connectivity & schema tests (5 tests)
│   └── test_agent.py            # LangGraph retry logic tests (4 tests, Mocked LLM)
│
├── .env.example                 # Template for environment variables
├── .gitignore                   # Ignores .env, venv, cache, bytecode
├── docker-compose.yml           # PostgreSQL container setup
├── requirements.txt             # Project dependencies
├── README.md                    # Project documentation
└── run.py                       # Unified CLI runner script
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+
- Docker & Docker Compose
- Google Gemini API Key ([Get one from Google AI Studio](https://aistudio.google.com/))

### 2. Clone & Setup Virtual Environment

```bash
# Clone the repository
git clone <your-repo-url>
cd nl-sql-business-analyst

# Create and activate virtual environment
python -m venv venv

# On Windows:
.\venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file from `.env.example`:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
DATABASE_URL=postgresql+psycopg://admin:admin@localhost:5432/business_db
```

### 5. Start PostgreSQL with Docker

```bash
docker compose up -d
```

Verify tables are seeded:

```bash
python run.py check
```

---

## 🖥️ How to Run

### Option A: Interactive CLI Agent
Run the standalone terminal interface:

```bash
python run.py cli
# or
python -m app.agent.graph
```

### Option B: FastAPI Backend
Start the REST API server on port 8001:

```bash
python run.py api
# or
uvicorn app.main:app --reload --port 8001
```
Interactive API docs available at: **http://localhost:8001/docs**

#### Example API Request:
```bash
curl -X POST "http://localhost:8001/ask" \
     -H "Content-Type: application/json" \
     -d '{"question": "What is the total revenue by product category?"}'
```

#### Example API Response:
```json
{
  "question": "What is the total revenue by product category?",
  "sql": "SELECT p.category, SUM(oi.quantity * p.price) AS total_revenue\nFROM products p\nJOIN order_items oi ON p.product_id = oi.product_id\nGROUP BY p.category\nORDER BY total_revenue DESC;",
  "columns": ["category", "total_revenue"],
  "rows": [
    {"category": "Electronics", "total_revenue": "123000.00"},
    {"category": "Accessories", "total_revenue": "6000.00"}
  ],
  "answer": "Here is the total revenue broken down by product category:\n\n* **Electronics:** $123,000.00\n* **Accessories:** $6,000.00",
  "error": null,
  "retry_count": 0
}
```

### Option C: Streamlit Web Dashboard
Launch the interactive web UI:

```bash
python run.py frontend
# or
streamlit run frontend/streamlit_app.py
```
Open **http://localhost:8501** in your browser.

---

## 🧪 Running Tests

Execute the automated Pytest suite (tests validator rules, database connection, and mocked LangGraph retry workflow):

```bash
python run.py test
# or
pytest -v
```

---

## 💡 Example Business Questions

- **Customer Insights**:
  - *"Which city has the most customers?"*
  - *"Who are our top 3 spending customers?"*
- **Sales & Revenue**:
  - *"What is the total revenue generated by each product category?"*
  - *"What are the top-selling products by quantity?"*
- **Order Analytics**:
  - *"List all orders placed in August 2026 along with the customer names."*
  - *"What is the average order value?"*

---

## 🔒 Security & Safety Notes

> [!IMPORTANT]
> The keyword-based validator (`app/database/validator.py`) provides an effective **first line of defense** by enforcing SELECT-only statements and blocking destructive keywords/injections.
>
> In production environments, follow defense-in-depth principles:
> 1. Create a dedicated read-only PostgreSQL user role:
>    ```sql
>    CREATE ROLE readonly_user WITH LOGIN PASSWORD 'password';
>    GRANT CONNECT ON DATABASE business_db TO readonly_user;
>    GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;
>    ```
> 2. Enforce query execution timeouts (`statement_timeout = '5s'`).
> 3. Limit maximum rows returned (`LIMIT 1000`).

---

## 🚀 Future Improvements

- [ ] Export query results directly to CSV / Excel reports from the Streamlit UI.
- [ ] Add conversation history memory for follow-up questions.
- [ ] Support multi-database engines (MySQL, Snowflake, BigQuery, SQLite).
