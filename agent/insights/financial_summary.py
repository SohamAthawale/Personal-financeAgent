# agent/insights/financial_summary.py

import json
import hashlib
from typing import Any, Dict, List
from pathlib import Path

# ==================================================
# LLM CONFIG
# ==================================================
try:
    from config.llm import LLM_ENABLED, LLM_MODEL
except ImportError:
    LLM_ENABLED = True
    LLM_MODEL = "llama3"

from agent.insights.utils import make_json_safe, call_llm

# ==================================================
# CACHE CONFIG
# ==================================================
CACHE_DIR = Path(".cache/insights")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_file(namespace: str) -> Path:
    return CACHE_DIR / f"financial_summary_{namespace}.json"


# ==================================================
# PROMPT
# ==================================================
SYSTEM_PROMPT = """
You are a financial reporting assistant.

STRICT RULES:
- Use ONLY the provided data
- Do NOT compute or infer numbers
- Do NOT classify or judge
- Restate values verbatim
"""


# ==================================================
# FINGERPRINT
# ==================================================
def _fingerprint(data: Dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


# ==================================================
# DERIVED METRICS (PURE MATH)
# ==================================================
def _derive_financial_metrics(metrics: Dict[str, Any]) -> Dict[str, Any]:
    income = metrics.get("total_income", 0) or 0
    expenses = metrics.get("total_expenses", 0) or 0
    withdrawals = metrics.get("withdrawal_count", 0) or 0
    deposits = metrics.get("deposit_count", 0) or 0

    return {
        "expense_to_income_ratio": (
            round(expenses / income, 4) if income > 0 else None
        ),
        "avg_expense_per_transaction": (
            round(expenses / withdrawals, 2) if withdrawals > 0 else None
        ),
        "avg_income_per_transaction": (
            round(income / deposits, 2) if deposits > 0 else None
        ),
        "transaction_frequency_ratio": (
            round(withdrawals / max(deposits, 1), 2)
        ),
        "net_cashflow": round(income - expenses, 2),
    }


# ==================================================
# CLASSIFIERS (RULES ONLY)
# ==================================================
def _classify_cashflow_health(metrics: Dict[str, Any]) -> str:
    income = metrics.get("total_income", 0) or 0
    net = metrics.get("net_cashflow", 0) or 0

    if income == 0:
        return "Unknown"

    ratio = abs(net) / income

    if net < 0 and ratio > 0.05:
        return "Low"
    if ratio <= 0.05:
        return "Moderate"
    return "High"


def _classify_patterns(
    metrics: Dict[str, Any],
    derived: Dict[str, Any],
) -> List[str]:
    flags: List[str] = []

    if derived.get("expense_to_income_ratio") is not None:
        if derived["expense_to_income_ratio"] > 1:
            flags.append("expenses_exceed_income")

    if derived.get("transaction_frequency_ratio", 0) > 5:
        flags.append("high_spending_frequency")

    if derived.get("avg_expense_per_transaction") is not None:
        if derived["avg_expense_per_transaction"] < 250:
            flags.append("micro_spending_pattern")

    if metrics.get("withdrawal_count", 0) > 2000:
        flags.append("very_high_transaction_volume")

    return flags


# ==================================================
# INSIGHT REGISTRY
# ==================================================
INSIGHT_REGISTRY = {
    "expenses_exceed_income": {
        "severity": "warning",
        "title": "Expenses exceed income",
        "description": (
            "Your total expenses are higher than your total income "
            "for this period."
        ),
    },
    "high_spending_frequency": {
        "severity": "info",
        "title": "High spending frequency",
        "description": (
            "You make a large number of transactions relative to "
            "your income events."
        ),
    },
    "micro_spending_pattern": {
        "severity": "info",
        "title": "Frequent small-value spending",
        "description": (
            "Your average spending per transaction is low, indicating "
            "many small purchases."
        ),
    },
    "very_high_transaction_volume": {
        "severity": "info",
        "title": "Very high transaction volume",
        "description": (
            "You have an unusually high number of transactions, which "
            "can make tracking finances harder."
        ),
    },
}


# ==================================================
# INSIGHT BUILDER (NO LLM)
# ==================================================
def _build_insights(metrics: Dict[str, Any]) -> Dict[str, Any]:
    derived = _derive_financial_metrics(metrics)
    flags = _classify_patterns(metrics, derived)

    cashflow_health = _classify_cashflow_health({
        **metrics,
        **derived,
    })

    insights = [
        INSIGHT_REGISTRY[flag]
        for flag in flags
        if flag in INSIGHT_REGISTRY
    ]

    return {
        "derived_metrics": derived,
        "cashflow_health": cashflow_health,
        "insights": insights,
    }


# ==================================================
# PUBLIC API
# ==================================================
def generate_financial_summary(
    metrics: Dict[str, Any],
    *,
    account_id: str | None = None,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """
    Generates a deep, safe financial summary.

    - All calculations are backend-only
    - LLM is used for wording only
    - Deterministic, cacheable, auditable
    """

    if not isinstance(metrics, dict) or not metrics:
        raise ValueError("metrics must be a non-empty dict")

    insights_payload = _build_insights(metrics)

    payload = {
        "metrics": make_json_safe(metrics),
        "insights": insights_payload,
    }

    fingerprint = _fingerprint(payload)
    cache_key = account_id or fingerprint[:12]
    cache_path = _cache_file(cache_key)

    # -------------------------------
    # Cache hit
    # -------------------------------
    if cache_path.exists() and not force_refresh:
        cached = json.loads(cache_path.read_text())
        if cached.get("fingerprint") == fingerprint:
            return {
                "type": "llm_financial_summary",
                "model": cached.get("model"),
                "content": cached.get("content"),
                "cached": True,
                "insights": insights_payload,
            }

    # -------------------------------
    # LLM disabled
    # -------------------------------
    if not LLM_ENABLED:
        return {
            "type": "llm_financial_summary",
            "model": None,
            "content": "LLM disabled. Metrics and insights are authoritative.",
            "cached": False,
            "insights": insights_payload,
        }

    prompt = f"""
{SYSTEM_PROMPT}

DATA:
{json.dumps(payload, indent=2)}

Respond EXACTLY in this format:

SUMMARY:
<one short paragraph>

CASHFLOW_HEALTH:
<verbatim value>
"""

    # -------------------------------
    # LLM Call
    # -------------------------------
    try:
        content = call_llm(prompt, temperature=0.05)

        cache_path.write_text(json.dumps({
            "fingerprint": fingerprint,
            "model": LLM_MODEL,
            "content": content,
        }, indent=2))

        return {
            "type": "llm_financial_summary",
            "model": LLM_MODEL,
            "content": content,
            "cached": False,
            "insights": insights_payload,
        }

    except Exception:
        return {
            "type": "llm_financial_summary",
            "model": None,
            "content": (
                "Summary unavailable. "
                "All financial metrics and insights remain authoritative."
            ),
            "cached": False,
            "degraded": True,
            "insights": insights_payload,
        }
