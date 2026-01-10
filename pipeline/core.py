from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import pandas as pd

# ==================================================
# USER / DB MODELS
# ==================================================
from models import User, Statement, Transaction
from agent.user_profile import UserProfile

# ==================================================
# PDF INTELLIGENCE
# ==================================================
from pdf_intelligence.stage1_layout import extract_layout
from pdf_intelligence.stage2_tables import detect_candidate_rows
from pdf_intelligence.stage6_orchestrator import choose_best_hypothesis
from pdf_intelligence.stage7_retry import retry_with_variants
from pdf_intelligence.stage8_llm_arbitration import llm_arbitrate
from pdf_intelligence.stage9_extraction import extract_transactions

# ==================================================
# ANALYTICS
# ==================================================
from analytics.metrics import compute_metrics_from_df
from analytics.categorization import (
    add_categories,
    category_summary,
    category_summary_all_debits,
)
from analytics.counterparty_analysis import upi_counterparty_summary
from analytics.merchant_normalizer import normalize_merchant

# ==================================================
# AGENT
# ==================================================
from agent.agent import run_agent

# ==================================================
# INSIGHTS
# ==================================================
from agent.insights.financial_summary import generate_financial_summary
from agent.insights.transaction_patterns import generate_transaction_patterns
from agent.insights.category_insights import generate_category_insights

# ==================================================
# HELPERS
# ==================================================
def transactions_to_df(transactions) -> pd.DataFrame:
    rows = []

    for t in transactions:
        amount = float(t.amount)

        rows.append(
            {
                "id": t.id,
                "date": t.date,
                "description": t.description,

                # CSV-era semantics (REQUIRED)
                "deposit": amount if amount > 0 else 0.0,
                "withdrawal": -amount if amount < 0 else 0.0,
                "amount": amount,

                # Optional / legacy
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

                # DB-native
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

    statement = Statement(
        user_id=user_id,
        original_filename=pdf_path
    )
    db.add(statement)
    db.flush()

    transactions = extract_transactions(
        rows=rows,
        schema=final["schema"],
        confidence=final["confidence"],
        source_pdf=pdf_path
    )

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
def compute_analytics(
    *,
    db: Session,
    user_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Deterministic financial analytics.

    Guarantees:
    - DB is the single source of truth
    - LLM runs ONLY for uncategorized transactions
    - Categorization is persisted (one-time)
    - Order-independent
    - Auditable & reproducible
    """

    q = (
        db.query(Transaction)
        .join(Statement)
        .filter(Statement.user_id == user_id)
    )

    if start_date:
        q = q.filter(Transaction.date >= start_date)
    if end_date:
        q = q.filter(Transaction.date < end_date)

    txns = q.all()

    if not txns:
        return {
            "status": "no_data",
            "metrics": None,
            "categories": [],
            "debits": [],
        }

    df = transactions_to_df(txns)

    merchant_data = df["description"].apply(normalize_merchant)
    df["merchant"] = merchant_data.apply(
        lambda x: (x.get("merchant_name") or "").upper()
    )
    df["upi_id"] = merchant_data.apply(lambda x: x.get("upi_id"))

    metrics, df_txn = compute_metrics_from_df(df)

    missing_mask = df_txn["category"].isna() | (df_txn["category"] == "")

    if missing_mask.any():
        df_missing = add_categories(df_txn[missing_mask].copy())
        txn_by_id = {t.id: t for t in txns}

        for _, row in df_missing.iterrows():
            txn = txn_by_id.get(row["id"])
            if txn:
                txn.category = row["category"]
                txn.category_confidence = row["category_confidence"]
                txn.category_source = row["category_source"]

        db.commit()

        df_txn.loc[
            missing_mask,
            ["category", "category_confidence", "category_source"],
        ] = df_missing[
            ["category", "category_confidence", "category_source"]
        ].values

    category_spending = category_summary(df_txn)
    all_debits = category_summary_all_debits(df_txn)
    upi_summary = upi_counterparty_summary(df_txn)

    metrics["top_upi_counterparties"] = upi_summary.to_dict(orient="records")

    return {
        "status": "success",
        "metrics": metrics,
        "categories": category_spending.to_dict(orient="records"),
        "debits": all_debits.to_dict(orient="records"),
    }

# ==================================================
# 3️⃣ INSIGHTS (LLM — READ ONLY)
# ==================================================
def generate_insights_view(
    *,
    db: Session,
    user_id: int,
    refresh: str | None = None,  # none | financial_summary | transaction_patterns | category_insights | all
) -> Dict[str, Any]:
    """
    Generate LLM-based financial insights for a user.

    FIXED VERSION:
    - Reuses analytics pipeline (single source of truth)
    - Never sends empty data to LLM
    - Never returns silent placeholders
    """

    # --------------------------------------------------
    # 1️⃣ Reuse deterministic analytics (CRITICAL FIX)
    # --------------------------------------------------
    analytics = compute_analytics(db=db, user_id=user_id)

    if analytics["status"] != "success":
        return {
            "status": "success",
            "financial_summary": {
                "type": "system",
                "model": None,
                "content": "No transactions available yet.",
                "status": "not_ready",
            },
            "transaction_patterns": {
                "type": "system",
                "model": None,
                "content": "No transaction data available yet.",
                "status": "not_ready",
            },
            "category_insights": {
                "type": "system",
                "model": None,
                "content": "No category data available yet.",
                "status": "not_ready",
            },
        }

    metrics = analytics["metrics"]
    category_data = analytics["categories"]

    # --------------------------------------------------
    # 2️⃣ Build lightweight txn sample (safe)
    # --------------------------------------------------
    txns = (
        db.query(Transaction)
        .join(Statement)
        .filter(Statement.user_id == user_id)
        .order_by(Transaction.date.desc())
        .limit(100)
        .all()
    )

    txn_sample = [
        {"date": t.date, "description": t.description}
        for t in txns
    ]

    refresh_all = refresh == "all"

    # --------------------------------------------------
    # 3️⃣ Generate insights (GUARDED)
    # --------------------------------------------------
    financial_summary = None
    transaction_patterns = None
    category_insights = None

    if metrics:
        financial_summary = generate_financial_summary(
            metrics,
            force_refresh=refresh_all or refresh == "financial_summary",
        )

    if txn_sample:
        transaction_patterns = generate_transaction_patterns(
            txn_sample,
            force_refresh=refresh_all or refresh == "transaction_patterns",
        )

    if category_data:
        category_insights = generate_category_insights(
            category_data,
            force_refresh=refresh_all or refresh == "category_insights",
        )

    # --------------------------------------------------
    # 4️⃣ Normalizer (NO SILENT FAILURES)
    # --------------------------------------------------
    def normalize(insight, fallback: str):
        if not insight or not insight.get("content"):
            return {
                "type": "system",
                "model": None,
                "content": fallback,
                "status": "not_ready",
            }

        return {
            "type": insight.get("type"),
            "model": insight.get("model"),
            "content": insight.get("content"),
            "status": "ready",
        }

    # --------------------------------------------------
    # 5️⃣ Final response
    # --------------------------------------------------
    return {
        "status": "success",
        "financial_summary": normalize(
            financial_summary,
            "Not enough data yet to generate a financial summary.",
        ),
        "transaction_patterns": normalize(
            transaction_patterns,
            "Not enough transactions yet to identify patterns.",
        ),
        "category_insights": normalize(
            category_insights,
            "Not enough categorized data yet to generate category insights.",
        ),
    }
#===================================================
# 4️⃣ AGENT
# ==================================================
def run_agent_view(*, db, user_id, goals=None):
    txns = (
        db.query(Transaction)
        .join(Statement)
        .filter(Statement.user_id == user_id)
        .all()
    )

    if not txns:
        return {"status": "no_data"}

    df = transactions_to_df(txns)
    metrics, df_txn = compute_metrics_from_df(df)

    return {
        "status": "success",
        **run_agent(df=df_txn, metrics=metrics, goals=goals),
    }
