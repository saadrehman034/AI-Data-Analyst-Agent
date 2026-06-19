# QueryMind — AI Data Analyst Agent

QueryMind lets non-technical users query a PostgreSQL database in plain English and get back answers as interactive charts, clean tables, and plain language explanations — powered by GPT-4o mini and a LangGraph state machine.

---

## Architecture

```
User Question
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│                    LangGraph State Machine               │
│                                                         │
│  load_schema ──► generate_sql ──► validate_sql          │
│                                        │                │
│                          ┌─── valid ───┤                │
│                          │             │                │
│                    execute_query   fix_sql ◄── retry    │
│                          │             │    (max 3x)    │
│                          ▼             │                │
│                    select_chart        │                │
│                          │             │                │
│                    generate_insight    │                │
│                          │             │                │
│                    build_response ◄────┘                │
└─────────────────────────────────────────────────────────┘
      │
      ▼
 FastAPI  ──► Next.js 14 UI
              ├── InsightCard  (plain English answer)
              ├── ChartRenderer (bar / line / pie / number / table)
              └── SQLViewer   (collapsible SQL code block)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | OpenAI GPT-4o mini |
| Agent orchestration | LangGraph |
| Backend API | FastAPI + asyncpg |
| Database | PostgreSQL 15+ |
| Frontend | Next.js 14 (App Router) |
| Charts | Recharts |
| Styling | Tailwind CSS |
| Language | Python 3.11+ · TypeScript 5 |

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+ running locally (or remote)
- An OpenAI API key

### 1. Clone and enter the project

```bash
git clone <repo>
cd querymind
```

### 2. Create the databases

Connect to PostgreSQL and create the two databases:

```sql
CREATE DATABASE querymind;
CREATE DATABASE business_data;
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in:

```env
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://postgres:password@localhost:5432/querymind
ANALYST_DB_URL=postgresql://postgres:password@localhost:5432/business_data
```

### 4. Install Python dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 5. Seed the sample database

This creates all tables and inserts 2,000 customers, 500 products, 10,000 orders, and more:

```bash
cd ..   # back to querymind/
python -m backend.db.seed
```

Seeding takes about 30–60 seconds.

### 6. Start the backend

```bash
uvicorn backend.main:app --reload --port 8000
```

Verify the API is healthy:

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "ok", "db": "connected", "analyst_db": "connected", "llm": "connected"}
```

### 7. Install frontend dependencies

```bash
cd frontend
npm install
```

### 8. Configure frontend environment

```bash
cp .env.local.example .env.local
```

The default `NEXT_PUBLIC_API_URL=http://localhost:8000` works out of the box.

### 9. Start the frontend

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## Test the API (curl)

```bash
# Submit a query
curl -s -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the top 5 product categories by revenue?", "session_id": "test-session"}' \
  | python -m json.tool

# Get schema
curl http://localhost:8000/schema | python -m json.tool

# Get suggested questions
curl http://localhost:8000/suggested-questions
```

---

## Example Questions to Try

1. What are the top 10 best-selling products by revenue?
2. Show me monthly revenue for the past 12 months
3. Which product categories generate the most profit margin?
4. What percentage of orders were cancelled last year?
5. Who are our top 10 customers by total spend?
6. What is the average order value by country?
7. How many new customers signed up each month this year?
8. What is the average satisfaction score by support ticket category?
9. Show me revenue by payment method
10. Which countries have the highest average order value?

---

## Screenshots

> Add screenshots here after first run.

---

## Project Structure

```
querymind/
├── backend/
│   ├── main.py                    FastAPI entry point + all endpoints
│   ├── config.py                  Settings loaded from .env
│   ├── agents/
│   │   ├── schema_agent.py        Loads and caches DB schema
│   │   ├── sql_agent.py           Generates SQL with GPT-4o mini
│   │   ├── validation_agent.py    EXPLAIN-validates SQL, fixes on failure
│   │   ├── insight_agent.py       Plain English explanation of results
│   │   └── chart_agent.py         Selects chart type for the data
│   ├── graph/
│   │   └── analyst_graph.py       LangGraph state machine wiring all nodes
│   ├── tools/
│   │   ├── db_tool.py             Executes SELECT queries, applies row cap
│   │   └── schema_tool.py         Reads schema with caching
│   ├── db/
│   │   ├── connection.py          asyncpg connection pools
│   │   ├── schema.sql             QueryMind app tables DDL
│   │   └── seed.py                Seeds 10k+ rows of realistic e-commerce data
│   ├── memory/
│   │   └── conversation_memory.py Per-session in-memory history
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── page.tsx               Main chat + visualisation interface
│   │   ├── history/page.tsx       Past queries grouped by session
│   │   └── schema/page.tsx        Full database schema explorer
│   ├── components/
│   │   ├── ChatInput.tsx          Question textarea with keyboard shortcut
│   │   ├── MessageBubble.tsx      User + agent message rendering
│   │   ├── ChartRenderer.tsx      Recharts bar/line/pie/number/table
│   │   ├── SQLViewer.tsx          Collapsible SQL with copy button
│   │   ├── InsightCard.tsx        Plain English answer card
│   │   ├── SchemaExplorer.tsx     Sidebar table/column browser
│   │   └── SuggestedQuestions.tsx Clickable example question chips
│   ├── lib/
│   │   ├── api.ts                 Typed fetch wrappers
│   │   └── types.ts               TypeScript interfaces
│   └── package.json
├── .env.example
└── README.md
```

---

## Conversation Memory

QueryMind maintains per-session conversation history in memory. This means follow-up questions work naturally:

> "Show me revenue by country"
> "Now filter that to just Europe"
> "Break it down by month"

The last 5 exchanges are passed to the SQL agent so it can resolve pronouns and relative references correctly. Sessions expire after 4 hours of inactivity.

---

## Error Handling

- **Invalid SQL**: automatically retried up to 3 times with the error fed back to GPT-4o mini
- **Empty results**: reported as `0 rows` with a clear insight message  
- **Backend errors**: user sees a friendly message, never a raw stack trace
- **LLM failures**: fallback heuristic chart selection keeps the UI responsive
