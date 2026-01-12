# agent/insights/financial_summary.py

import json
from typing import Any, Dict

# ==================================================
# BACKEND CONFIG
# ==================================================
try:
    from config.llm import LLM_ENABLED, LLM_MODEL
except ImportError:
    LLM_ENABLED = True
    LLM_MODEL = "llama3"

from agent.insights.utils import make_json_safe, call_llm


# ==================================================
# SYSTEM PROMPT (STRICT, METRIC-LOCKED)
# ==================================================
SYSTEM_PROMPT = """
You are a financial reporting assistant.

STRICT RULES:
- Use ONLY the provided metrics
- Restate totals verbatim
- Do NOT mention transactions
- Do NOT compute or infer numbers
"""


# ==================================================
# FINANCIAL SUMMARY GENERATOR (BACKEND ONLY)
# ==================================================
def generate_financial_summary(
    metrics: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generates a qualitative financial summary.

    - Backend-only
    - Metrics are authoritative
    - Safe to expose via API
    """

    # -------------------------------
    # Hard guards
    # -------------------------------
    if not LLM_ENABLED:
        return {
            "type": "llm_financial_summary",
            "model": None,
            "content": "LLM disabled by server configuration."
        }

    if not isinstance(metrics, dict):
        raise ValueError("metrics must be a dict")

    # -------------------------------
    # JSON-safe metrics
    # -------------------------------
    safe_metrics = make_json_safe(metrics)

    # -------------------------------
    # Prompt
    # -------------------------------
    prompt = f"""
{SYSTEM_PROMPT}

AUTHORITATIVE_METRICS:
{json.dumps(safe_metrics, indent=2)}

Provide:
1. Income, expense, net cashflow summary
2. Cashflow health (Low / Moderate / High)

Do NOT invent numbers.
If unsure, restate the provided totals.
"""

    # -------------------------------
    # LLM Call (via shared utility)
    # -------------------------------
    try:
        content = call_llm(
            prompt,
            temperature=0.05
        )

        return {
            "type": "llm_financial_summary",
            "model": LLM_MODEL,
            "content": content
        }

    except Exception:
        return {
            "type": "llm_financial_summary",
            "model": None,
            "content": (
                "Financial summary unavailable.\n"
                "Authoritative metrics remain valid."
            )
        }
