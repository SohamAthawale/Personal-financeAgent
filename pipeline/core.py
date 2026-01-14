from typing import Dict, Any
from sqlalchemy.orm import Session

from agent.user_profile import UserProfile
from models import User
from models import FinancialGoal
from agent.goal_engine import FinancialGoal as FinancialGoalEngine

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
                "id": t.id,
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
from datetime import datetime
from typing import Dict, Any, Optional
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

from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from models import Transaction, Statement
from analytics.metrics import compute_metrics_from_df
from analytics.categorization import (
    add_categories,
    category_summary,
    category_summary_all_debits,
)
from analytics.counterparty_analysis import upi_counterparty_summary

from typing import Dict, Any, Optional
from datetime import datetime
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
from analytics.merchant_normalizer import normalize_merchant


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

    # --------------------------------------------------
    # 1️⃣ Fetch transactions (DB = source of truth)
    # --------------------------------------------------
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

    # --------------------------------------------------
    # 2️⃣ Empty-state safety
    # --------------------------------------------------
    if not txns:
        return {
            "status": "no_data",
            "message": "No transactions found for this period.",
            "period": {
                "type": "custom" if start_date or end_date else "all_time",
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
            },
            "metrics": None,
            "categories": [],
            "debits": [],
        }

    # --------------------------------------------------
    # 3️⃣ Convert DB rows → DataFrame
    # --------------------------------------------------
    df = transactions_to_df(txns)

    # --------------------------------------------------
    # 🔧 ALWAYS derive merchant + UPI metadata (NO LLM)
    # --------------------------------------------------
    merchant_data = df["description"].apply(normalize_merchant)

    df["merchant"] = merchant_data.apply(
        lambda x: (x.get("merchant_name") or "").upper()
    )

    df["upi_id"] = merchant_data.apply(
        lambda x: x.get("upi_id")
    )

    # --------------------------------------------------
    # 4️⃣ Core metrics (GROUND TRUTH)
    # --------------------------------------------------
    metrics, df_txn = compute_metrics_from_df(df)

    # --------------------------------------------------
    # 5️⃣ Financial invariants (HARD GUARDS)
    # --------------------------------------------------
    assert metrics["total_income"] >= 0, "Income cannot be negative"
    assert metrics["total_expense"] >= 0, "Expense cannot be negative"

    delta = (
        metrics["total_income"]
        - metrics["total_expense"]
        - metrics["net_cashflow"]
    )
    assert abs(delta) < 0.01, "Cashflow invariant violated"

    # --------------------------------------------------
    # 6️⃣ LAZY CATEGORIZATION (ONLY IF MISSING)
    # --------------------------------------------------
    missing_mask = (
        df_txn["category"].isna()
        | (df_txn["category"] == "")
    )

    if missing_mask.any():
        df_missing = df_txn[missing_mask].copy()

        # 🔥 Rules + LLM pipeline
        df_missing = add_categories(df_missing)

        # Persist back to DB (ONE TIME)
        txn_by_id = {t.id: t for t in txns}

        for _, row in df_missing.iterrows():
            txn = txn_by_id.get(row["id"])
            if not txn:
                continue

            txn.category = row["category"]
            txn.category_confidence = row["category_confidence"]
            txn.category_source = row["category_source"]

        db.commit()

        # Merge results back
        df_txn.loc[
            missing_mask,
            ["category", "category_confidence", "category_source"],
        ] = df_missing[
            ["category", "category_confidence", "category_source"]
        ].values

    # 🔐 Safety: analytics must never see uncategorized rows
    assert not df_txn["category"].isna().any(), "Uncategorized txns remain"

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
        "llm_backfilled": int(missing_mask.sum()),
    }

    # --------------------------------------------------
    # 9️⃣ Period metadata
    # --------------------------------------------------
    period_meta = {
        "type": "all_time",
        "start": None,
        "end": None,
    }

    if start_date or end_date:
        period_meta = {
            "type": "custom",
            "start": start_date.isoformat() if start_date else None,
            "end": end_date.isoformat() if end_date else None,
        }

    # --------------------------------------------------
    # 🔟 Final payload
    # --------------------------------------------------
    return {
        "status": "success",
        "period": period_meta,
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
from pipeline.core import compute_analytics

from agent.insights.financial_summary import generate_financial_summary
from agent.insights.transaction_patterns import generate_transaction_patterns
from agent.insights.category_insights import generate_category_insights


def generate_insights_view(
    *,
    db: Session,
    user_id: int,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Generate LLM-based insights STRICTLY from analytics output.

    Behavior:
    - force_refresh=True  → hard refresh (bypass all insight caches)
    - force_refresh=False → normal cached behavior

    Guarantees:
    - compute_analytics is the ONLY source of truth
    - No recomputation of metrics
    - No re-categorization
    - LLM used only for explanation, never for math
    """

    # --------------------------------------------------
    # 1️⃣ Authoritative analytics (single engine)
    # --------------------------------------------------
    analytics = compute_analytics(
        db=db,
        user_id=user_id
    )

    # --------------------------------------------------
    # 2️⃣ Graceful empty / no-data handling
    # --------------------------------------------------
    if analytics["status"] != "success":
        return {
            "status": analytics["status"],
            "message": analytics.get(
                "message",
                "No data available for insights."
            ),
            "financial_summary": None,
            "transaction_patterns": None,
            "category_insights": None,
        }

    metrics = analytics["metrics"]
    categories = analytics["categories"]

    # --------------------------------------------------
    # 3️⃣ Lightweight transaction sample (patterns ONLY)
    # --------------------------------------------------
    txns_sample = (
        db.query(
            Transaction.date,
            Transaction.description,
            Transaction.merchant,
            Transaction.amount,
            Transaction.category,
        )
        .join(Statement)
        .filter(Statement.user_id == user_id)
        .order_by(Transaction.date.desc())
        .limit(50)
        .all()
    )

    transaction_patterns_input = [
        {
            "date": t.date,
            "description": t.description,
            "merchant": t.merchant,
            "amount": float(t.amount),
            "category": t.category,
        }
        for t in txns_sample
    ]

    # --------------------------------------------------
    # 4️⃣ LLM = explanation layer ONLY
    # --------------------------------------------------
    return {
        "status": "success",

        # 🔒 Uses authoritative metrics only
        "financial_summary": generate_financial_summary(
            metrics,
            force_refresh=force_refresh
        ),

        # 🔒 Uses authoritative category totals
        "category_insights": generate_category_insights(
            categories,
            force_refresh=force_refresh
        ),

        # 🔒 Pattern-only, no math
        "transaction_patterns": generate_transaction_patterns(
            transaction_patterns_input,
            force_refresh=force_refresh
        ),
    }

# ==================================================
# 4️⃣ AGENT
# ==================================================
def run_agent_view(*, db, user_id, goals=None):
    # --------------------------------------------------
    # 1️⃣ Fetch transactions
    # --------------------------------------------------
    txns = (
        db.query(Transaction)
        .join(Statement)
        .filter(Statement.user_id == user_id)
        .all()
    )

    if not txns:
        return {
            "status": "no_data",
            "message": "No transactions found",
        }

    # --------------------------------------------------
    # 2️⃣ Convert to DataFrame + compute metrics
    # --------------------------------------------------
    df = transactions_to_df(txns)
    metrics, df_txn = compute_metrics_from_df(df)

    # --------------------------------------------------
    # 3️⃣ Load remembered goals if none provided
    # --------------------------------------------------
    if goals is None:
        db_goals = (
            db.query(FinancialGoal)
            .filter(
                FinancialGoal.user_id == user_id,
                FinancialGoal.is_active.is_(True),
            )
            .all()
        )

        goals = [
            FinancialGoalEngine(
                name=g.name,
                target_amount=g.target_amount,
                deadline=g.deadline,
                priority=g.priority,
            )
            for g in db_goals
        ]

    # --------------------------------------------------
    # 4️⃣ Deterministic goal evaluation (MATH ONLY)
    # --------------------------------------------------
    from agent.goal_engine import (
        evaluate_goal,
        goal_based_action,
        build_goal_projection,
    )
    from agent.insights.goal_insights import generate_goal_insights

    goal_evaluations = []
    goal_actions = []

    for goal in goals:
        eval_result = evaluate_goal(goal, metrics)

        # 📈 build chart-ready projection
        projection_series = build_goal_projection(eval_result)

        goal_evaluations.append({
            **eval_result,
            "projection_series": projection_series,
        })

        goal_actions.append(
            goal_based_action(eval_result)
        )

    # --------------------------------------------------
    # 5️⃣ LLM explanations (WORDS ONLY)
    # --------------------------------------------------
    llm_goal_insights = generate_goal_insights(
        goal_evaluations,
        force_refresh=False,
    )

    # --------------------------------------------------
    # 6️⃣ Final response (UI + charts ready)
    # --------------------------------------------------
    return {
        "status": "success",

        # 📊 overall analytics (optional dashboard use)
        "metrics": metrics,

        # 🎯 per-goal math + timelines (GRAPH INPUT)
        "goal_evaluations": goal_evaluations,

        # 🧠 recommendations (rules + LLM)
        "recommendations": {
            "goals": goal_actions + llm_goal_insights
        },
    }
