from typing import Dict, Any
from sqlalchemy.orm import Session

from agent.user_profile import UserProfile

# PDF intelligence
from pdf_intelligence.stage1_layout import extract_layout
from pdf_intelligence.stage2_tables import detect_candidate_rows
from pdf_intelligence.stage6_orchestrator import choose_best_hypothesis
from pdf_intelligence.stage7_retry import retry_with_variants
from pdf_intelligence.stage8_llm_arbitration import llm_arbitrate
from pdf_intelligence.stage9_extraction import extract_transactions

# Analytics
from analytics.metrics import compute_metrics_from_df
from analytics.categorization import (
    add_categories,
    category_summary,
    category_summary_all_debits
)
from analytics.counterparty_analysis import upi_counterparty_summary

# Agent
from agent.agent import run_agent
from agent.insights.financial_summary import generate_financial_summary
from agent.insights.transaction_patterns import generate_transaction_patterns
from agent.insights.category_insights import generate_category_insights
from agent.insights.utils import make_json_safe

# DB models
from models import Statement, Transaction

import pandas as pd


# ==================================================
# HELPERS
# ==================================================
def transactions_to_df(transactions) -> pd.DataFrame:
    rows = []

    for t in transactions:
        amount = float(t.amount)

        rows.append(
            {
                "date": t.date,
                "description": t.description,

                # CSV-era semantics (REQUIRED by analytics)
                "deposit": amount if amount > 0 else 0.0,
                "withdrawal": -amount if amount < 0 else 0.0,
                "amount": amount,

                # Optional / legacy fields
                "balance": (
                    t.raw.get("balance")
                    if isinstance(t.raw, dict)
                    else None
                ),
                "confidence": (
                    t.raw.get("confidence", 1.0)
                    if isinstance(t.raw, dict)
                    else 1.0
                ),

                # New DB-native fields
                "merchant": t.merchant,
                "category": t.category,
                "txn_type": t.txn_type,
            }
        )

    return pd.DataFrame(rows)


# ==================================================
# 1️⃣ PARSE STATEMENT (UPLOAD)
# ==================================================
def parse_statement(
    *,
    db: Session,
    pdf_path: str,
    user_id: int
) -> Dict[str, Any]:

    words = extract_layout(pdf_path)
    rows = detect_candidate_rows(words)

    schema, confidence = choose_best_hypothesis(rows)

    if confidence < 0.9:
        final = retry_with_variants(rows, choose_best_hypothesis)
        if final.get("decision") == "needs_arbitration":
            final = llm_arbitrate([final]) or final
    else:
        final = {"schema": schema, "confidence": confidence}

    if not final.get("schema"):
        return {"status": "error", "message": "Schema detection failed"}

    # Create statement row
    statement = Statement(
        user_id=user_id,
        original_filename=pdf_path
    )
    db.add(statement)
    db.flush()  # get statement.id

    transactions = extract_transactions(
        rows=rows,
        schema=final["schema"],
        confidence=final["confidence"],
        source_pdf=pdf_path
    )

    # Persist transactions
    db.bulk_save_objects(
        [
            Transaction(
                statement_id=statement.id,
                date=txn["date"],
                description=txn["description"],
                merchant=txn.get("merchant"),
                amount=txn["amount"],
                txn_type=txn.get("type"),
                raw=txn,
            )
            for txn in transactions
        ]
    )

    db.commit()

    return {
        "status": "success",
        "statement_id": statement.id,
        "transaction_count": len(transactions),
        "schema_confidence": final["confidence"],
    }


# ==================================================
# 2️⃣ ANALYTICS (DASHBOARD)
# ==================================================
from typing import Dict, Any
from sqlalchemy.orm import Session

from models import Transaction, Statement
from pipeline.core import transactions_to_df

from analytics.metrics import compute_metrics_from_df
from analytics.categorization import (
    add_categories,
    category_summary,
    category_summary_all_debits,
)
from analytics.counterparty_analysis import upi_counterparty_summary


def compute_analytics(
    *,
    db: Session,
    user_id: int
) -> Dict[str, Any]:
    """
    Deterministic financial analytics.

    Guarantees:
    - Uses ONLY DB-persisted transactions
    - No LLM involvement
    - Order-independent
    - Auditable & reproducible
    """

    # --------------------------------------------------
    # 1️⃣ Fetch transactions (DB = source of truth)
    # --------------------------------------------------
    txns = (
        db.query(Transaction)
        .join(Statement)
        .filter(Statement.user_id == user_id)
        .all()
    )

    # --------------------------------------------------
    # 2️⃣ Empty-state safety
    # --------------------------------------------------
    if not txns:
        return {
            "status": "no_data",
            "message": "No transactions found. Upload a bank statement.",
            "metrics": None,
            "categories": [],
            "debits": [],
        }

    # --------------------------------------------------
    # 3️⃣ Convert DB rows → analytics DataFrame
    # --------------------------------------------------
    df = transactions_to_df(txns)

    # --------------------------------------------------
    # 4️⃣ Compute core metrics (GROUND TRUTH)
    # --------------------------------------------------
    metrics, df_txn = compute_metrics_from_df(df)

    # --------------------------------------------------
    # 5️⃣ Financial invariants (HARD GUARDS)
    # --------------------------------------------------
    assert metrics["total_income"] >= 0, "Income cannot be negative"
    assert metrics["total_expense"] >= 0, "Expense cannot be negative"

    # income - expense ≈ net_cashflow
    delta = (
        metrics["total_income"]
        - metrics["total_expense"]
        - metrics["net_cashflow"]
    )
    assert abs(delta) < 0.01, "Cashflow invariant violated"

    # --------------------------------------------------
    # 6️⃣ Categorization (pure transformation)
    # --------------------------------------------------
    df_txn = add_categories(df_txn)

    # --------------------------------------------------
    # 7️⃣ Aggregations
    # --------------------------------------------------
    category_spending = category_summary(df_txn)
    all_debits = category_summary_all_debits(df_txn)
    upi_summary = upi_counterparty_summary(df_txn)

    metrics["top_upi_counterparties"] = (
        upi_summary.to_dict(orient="records")
    )

    # --------------------------------------------------
    # 8️⃣ Audit metadata (DEBUG + TRUST)
    # --------------------------------------------------
    metrics["_audit"] = {
        "transaction_count": int(len(df_txn)),
        "sum_deposits": round(float(df_txn["deposit"].sum()), 2),
        "sum_withdrawals": round(float(df_txn["withdrawal"].sum()), 2),
    }

    # --------------------------------------------------
    # 9️⃣ Final payload
    # --------------------------------------------------
    return {
        "status": "success",
        "metrics": metrics,
        "categories": category_spending.to_dict(orient="records"),
        "debits": all_debits.to_dict(orient="records"),
    }


# ==================================================
# 3️⃣ INSIGHTS (LLM)
# ==================================================
from typing import Dict, Any
from sqlalchemy.orm import Session

from models import Transaction, Statement
from analytics.metrics import compute_metrics_from_df
from analytics.categorization import (
    add_categories,
    category_summary,
)
from pipeline.core import transactions_to_df


from agent.insights.financial_summary import generate_financial_summary
from agent.insights.transaction_patterns import generate_transaction_patterns
from agent.insights.category_insights import generate_category_insights


def generate_insights_view(
    *,
    db: Session,
    user_id: int
) -> Dict[str, Any]:
    """
    Generate LLM-based financial insights for a user.

    Safe behavior:
    - If user has no transactions → return graceful `no_data` response
    - Never raises on empty datasets
    """

    # --------------------------------------------------
    # Fetch user transactions
    # --------------------------------------------------
    txns = (
        db.query(Transaction)
        .join(Statement)
        .filter(Statement.user_id == user_id)
        .all()
    )

    # --------------------------------------------------
    # Graceful empty state (IMPORTANT)
    # --------------------------------------------------
    if not txns:
        return {
            "status": "no_data",
            "message": "No transactions found. Upload a bank statement to generate insights.",
            "financial_summary": None,
            "transaction_patterns": None,
            "category_insights": None,
        }

    # --------------------------------------------------
    # Convert to DataFrame
    # --------------------------------------------------
    df = transactions_to_df(txns)

    # --------------------------------------------------
    # Metrics (guaranteed non-empty here)
    # --------------------------------------------------
    metrics, _ = compute_metrics_from_df(df)

    # --------------------------------------------------
    # Categorization
    # --------------------------------------------------
    df = add_categories(df)

    # --------------------------------------------------
    # LLM Insights
    # --------------------------------------------------
    return {
        "status": "success",

        "financial_summary": generate_financial_summary(metrics),

        "transaction_patterns": generate_transaction_patterns(
            df[["date", "description"]].to_dict(orient="records")
        ),

        "category_insights": generate_category_insights(
            category_summary(df).to_dict(orient="records")
        ),
    }


# ==================================================
# 4️⃣ AGENT
# ==================================================
def run_agent_view(
    *,
    db: Session,
    user: UserProfile
) -> Dict[str, Any]:

    txns = (
        db.query(Transaction)
        .join(Statement)
        .filter(Statement.user_id == user.id)
        .all()
    )

    df = transactions_to_df(txns)
    metrics = compute_metrics_from_df(df)

    result = run_agent(
        df=df,
        metrics=metrics,
        user=user
    )

    return make_json_safe(result)
