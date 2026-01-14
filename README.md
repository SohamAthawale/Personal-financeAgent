# 📊 AI-Powered Financial Intelligence Platform

A **full-stack, production-grade financial intelligence system** that transforms raw bank statement PDFs into **structured transactions, analytics, forecasts, goals, risks, and AI-generated insights** using a **policy-guided, multi-stage LLM architecture**.

This project is **not a demo** or a thin LLM wrapper.  
It is a **stateful, fault-tolerant, goal-aware financial reasoning engine** with a modern frontend and a carefully constrained LLM strategy.

---

## 🚀 What This System Does

At a high level, the platform:

- Accepts **bank statement PDFs**
- Extracts transactions using a **multi-stage LLM + rules pipeline**
- Normalizes merchants and categorizes spending
- Builds a **persistent financial state and memory**
- Computes **analytics, risks, anomalies, and forecasts**
- Evaluates **user-defined financial goals**
- Generates **grounded AI insights**
- Presents everything through a **React dashboard**

> Every step is designed for **correctness, traceability, and robustness**, not just “LLM magic”.

---

## ✨ Core Features

### 📄 Ingestion & Extraction
- PDF bank statement upload  
- Multi-layout and multi-bank support  
- Structured transaction extraction  
- Confidence scoring per transaction  

### 🧠 LLM-Driven Intelligence (Safely Constrained)
- Local **Ollama models**
- Intelligent, context-aware prompting
- Policy-validated outputs
- Retry & arbitration logic
- **Zero blind trust** in LLM responses

### 🏷️ Data Normalization
- Merchant name normalization
- Counterparty identification
- Learned merchant memory
- Stable category mapping

### 📊 Analytics
- Income, expenses, savings
- Category-wise breakdowns
- Period & month-based views

### 🎯 Goals & Forecasting
- Goal creation (amount, deadline, priority)
- Feasibility evaluation
- Monthly savings requirements
- Projection charts
- Goal-specific insights

### ⚠️ Risk & Anomaly Detection
- Unusual transaction detection
- Expense drift
- Behavioral anomalies
- Recurring subscriptions

### 🧠 State, Memory & Policy
- Persistent financial state
- Cross-session memory
- Rule-based decision policies
- Guardrails for AI outputs

### 📈 AI Insights
- Financial summaries
- Category insights
- Transaction pattern explanations
- Goal-aware recommendations

### 🌐 Frontend
- React + TypeScript
- Clean, responsive UI
- Charts & projections
- Real-time upload feedback

---

## 🏗️ System Architecture (High Level)
React Frontend
↓
Flask API (app.py)
↓
Multi-Stage Intelligence Engine
↓
State / Memory / Policy Layer
↓
Database (db.py)
↓
AI Insights & Responses

The system is **API-first**, **stateful**, and **LLM-agnostic**.

---

## ⚙️ Backend Entry Points

### `app.py` — Flask Application

**Main backend entry point**

**Responsibilities**
- Initializes Flask app
- Configures CORS & sessions
- Handles authentication
- Exposes REST APIs used by the frontend
- Delegates logic to internal engines

**Typical endpoints**
- Upload & parse statements  
- Fetch analytics  
- Fetch insights  
- Manage goals  
- Generate recommendations  

> `app.py` contains **no heavy business logic**.  
> All intelligence lives in dedicated modules.

---

### `db.py` — Database Layer

Centralized database abstraction.

**Responsibilities**
- Connection setup
- Session lifecycle
- Safe query execution
- Isolation of persistence logic

**Enables**
- Clean separation of concerns
- Easy testing
- Database portability

---

## 🧩 Core Backend Architecture (Detailed)

### 1️⃣ Multi-Stage Extraction Pipeline

**Heart of the system**

**Files**
- `stage1_layout.py` – Detects document layout
- `stage2_tables.py` – Extracts candidate tables
- `stage3_hypotheses.py` – Generates multiple extraction hypotheses
- `stage4_dates.py` – Date inference & normalization
- `stage4_validation.py` – Schema & consistency checks
- `stage5_confidence.py` – Confidence scoring
- `stage6_orchestrator.py` – Pipeline coordinator
- `stage7_retry.py` – Intelligent retries
- `stage8_llm_arbitration.py` – LLM-based conflict resolution
- `stage9_extraction.py` – Final structured output

**Why this exists**
- Bank PDFs are inconsistent
- Single-pass LLM extraction is fragile
- Financial data requires correctness

**Guarantees**
- Multiple attempts
- Validation at every stage
- Arbitration instead of silent failure

---

### 2️⃣ Categorization & Merchant Intelligence

**Files**
- `merchant_normalizer.py`
- `merchant_memory.py`
- `counterparty_analysis.py`
- `categorization.py`
- `llm_categorizer.py`
- `llm_name_classifier.py`
- `categories.py`
- `category_model.py`

**Capabilities**
- Canonical merchant naming
- Stable category assignment
- Learning from historical corrections
- LLM fallback when rules are insufficient

---

### 3️⃣ State, Memory & Policy Layer

**What makes the system intelligent over time**

**Files**
- `state.py` – Core state schema
- `state_builder.py` – Builds enriched state
- `memory.py` – Persistent behavioral memory
- `policy.py` – Decision guardrails
- `storage.py` – Persistence abstraction
- `metrics.py` – System & financial metrics

**Used to**
- Maintain user context
- Enforce constraints
- Prevent unsafe AI outputs
- Enable long-term reasoning

---

### 4️⃣ Risk, Anomaly & Pattern Detection

**Files**
- `risk.py`
- `anomaly.py`
- `recurring.py`
- `transaction_patterns.py`

**Detects**
- Suspicious transactions
- Behavioral shifts
- Subscriptions & recurring expenses
- Expense drift

---

### 5️⃣ Goals, Forecasting & Decision Engine

**Files**
- `goal_parser.py`
- `goal_engine.py`
- `goal_insights.py`
- `forecast.py`
- `features.py`
- `executor.py`

**Capabilities**
- Goal parsing
- Feasibility evaluation
- Monthly savings requirements
- Time-based projections
- Goal-aware recommendations

---

### 6️⃣ Insights & Summarization

**Files**
- `financial_summary.py`
- `category_insights.py`
- `insights_agent.py`

**Produces**
- Human-readable insights grounded in:
  - Computed metrics
  - Detected patterns
  - Goal evaluations

---

## 🤖 LLM Strategy (Critical Design Section)

### Local Ollama Models
- All LLMs run **locally using Ollama**
- No external API dependency
- Full data privacy
- Low latency
- Complete model control

### Intelligent Prompting
- Context-aware prompts
- Built using:
  - Extracted structure
  - State
  - Memory
  - Prior hypotheses
- Each stage has **task-specific prompts**

### Policy-Guided Outputs (No Blind Trust)
LLM outputs are **never accepted directly**.

They are validated through:
- Schema checks
- Domain rules
- Policy constraints
- Confidence thresholds

Failures trigger:
- Retries
- Alternative prompts
- Arbitration

### Arbitration & Retry Logic
- Multiple outputs compared
- Confidence-weighted resolution
- Secondary LLM judgment when needed
- Deterministic logic has final authority

### LLMs Are Not Decision Makers
LLMs act as:
- Reasoning assistants
- Pattern detectors
- Hypothesis generators

Final decisions are made by:
- Policy
- State
- Execution logic

> **This is production-safe LLM usage.**

---

## 🎨 Frontend (React + TypeScript)

**Pages**
- `Login.tsx` – Authentication
- `Onboarding.tsx` – Account creation
- `Dashboard.tsx` – PDF upload & parsing
- `Analytics.tsx` – Financial analytics
- `Goals.tsx` – Goals & projections
- `Insights.tsx` – AI insights

**Frontend Principles**
- API-driven
- Clear UX for complex AI workflows
- Safe error handling
- Responsive design

---

## 🔁 End-to-End Flow

1. User uploads PDF
2. Flask API receives file
3. Multi-stage pipeline extracts transactions
4. Merchants & categories normalized
5. State & memory updated
6. Analytics, risks & forecasts computed
7. AI insights generated
8. Results displayed in UI

---

## 🛠️ Tech Stack

### Backend
- Python
- Flask
- PostgreSQL
- Ollama (local LLMs)

### Frontend
- React
- TypeScript
- Tailwind CSS
- Recharts

---

## 🧠 Design Philosophy

- Correctness over cleverness
- State over stateless prompts
- LLMs as tools, not authorities
- Validation over blind trust
- Architecture before optimization

---

## 🔮 Future Enhancements

- Budget planning engine
- Multi-account support
- Explainable AI traces
- Real-time alerts
- Mobile-first UI
