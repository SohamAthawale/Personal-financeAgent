# Personal Finance Agent

AI-powered financial intelligence platform that turns bank statement PDFs into structured transactions, analytics, goals, risks, forecasts, and AI insights using a policy-guided multi-stage LLM pipeline.

## Key Capabilities
- PDF statement ingestion and multi-stage extraction with validation and arbitration
- Merchant normalization and categorization with memory and ML fallback
- Analytics, anomalies, goals, and forecasting
- Local LLM support via Ollama with policy guardrails
- React + TypeScript dashboard

## Architecture
React UI -> Flask API -> PDF intelligence pipeline -> State/Policy/Memory -> PostgreSQL -> Analytics + Insights

## Prerequisites
- Python 3.10+
- Node 18+
- PostgreSQL
- Ollama (optional; required if `LLM_ENABLED=true`)

## Environment Variables
Defaults live in `config/llm.py` and `db.py`.

| Variable | Default | Description |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+psycopg2://finance_user@localhost:5432/finance_agent` | SQLAlchemy database URL |
| `JWT_SECRET_KEY` | `super-secret-key` | JWT signing key (set this in real deployments) |
| `LLM_ENABLED` | `true` | Enable or disable LLM calls |
| `OLLAMA_URL` | `http://localhost:11434/api/generate` | Ollama generate endpoint |
| `LLM_MODEL` | `qwen2.5:7b-instruct` | Ollama model name |

A starter file is provided at `.env.example`.

## Backend Setup
1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure your database URL in `DATABASE_URL` (or edit `db.py`).
4. Initialize the database schema:

```bash
python init_db.py
```

5. Start the API server:

```bash
python app.py
```

The API runs at `http://127.0.0.1:5000` by default.

## Frontend Setup
1. `cd frontend/Web`
2. `npm install`
3. `npm run dev`

Vite serves the app at `http://localhost:5173` by default.

## Quickstart (API)
1. Register a user:

```bash
curl -X POST http://127.0.0.1:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"password123"}'
```

2. Login and capture the token:

```bash
curl -X POST http://127.0.0.1:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"password123"}'
```

3. Upload a statement PDF:

```bash
curl -X POST http://127.0.0.1:5000/api/statement/parse \
  -H "Authorization: Bearer <TOKEN>" \
  -F "file=@/absolute/path/to/statement.pdf"
```

4. Fetch analytics for the last 3 months:

```bash
curl "http://127.0.0.1:5000/api/statement/analytics?period=3m" \
  -H "Authorization: Bearer <TOKEN>"
```

5. Fetch insights (force refresh):

```bash
curl "http://127.0.0.1:5000/api/statement/insights?force_refresh=true" \
  -H "Authorization: Bearer <TOKEN>"
```

6. Create goals:

```bash
curl -X POST http://127.0.0.1:5000/api/goals \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"goals":[{"name":"Emergency Fund","target_amount":2000,"deadline":"2025-06-30","priority":"high"}]}'
```

## API Endpoints (Summary)
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/statement/parse`
- `GET /api/statement/analytics`
- `GET /api/statement/insights`
- `POST /api/agent/recommendations`
- `GET /api/goals`
- `POST /api/goals`
- `DELETE /api/goals/<id>`
- `GET /api/transactions`
- `GET /api/transaction/explain/<id>`
- `POST /api/transaction/correct`
- `GET /health/db`

See `app.py` for request and response details.

## Project Layout
- `app.py` Flask API
- `db.py` database configuration
- `models.py` SQLAlchemy models
- `pipeline/` pipeline core orchestration
- `pdf_intelligence/` multi-stage PDF extraction
- `analytics/` metrics, categorization, and risk logic
- `agent/` goal evaluation and insight generation
- `frontend/Web/` React UI (Vite + TypeScript)
- `uploads/` incoming PDFs
- `output/` pipeline outputs

## Security Notes
- `JWT_SECRET_KEY` should be set via environment variable for any shared or production deployment.
