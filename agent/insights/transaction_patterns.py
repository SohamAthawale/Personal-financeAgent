# agent/insights/transaction_patterns.py

import json
from typing import Any, Dict, List

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
# SYSTEM PROMPT (STRICT, QUALITATIVE ONLY)
# ==================================================
SYSTEM_PROMPT = """
You are a transaction pattern analyst.

STRICT RULES:
- Transactions are qualitative only
- Do NOT compute totals
- Do NOT invent amounts
- Use words like: frequent, clustered, large, repeated
"""


# ==================================================
# TRANSACTION PATTERN ANALYZER (BACKEND ONLY)
# ==================================================
def generate_transaction_patterns(
    transactions: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Generates qualitative transaction pattern insights.

    - Backend-only
    - Uses samples only
    - No numeric inference
    - Safe to expose via API
    """

    # -------------------------------
    # Hard guards
    # -------------------------------
    if not LLM_ENABLED:
        return {
            "type": "llm_transaction_patterns",
            "model": None,
            "content": "LLM disabled by server configuration."
        }

    if not isinstance(transactions, list):
        raise ValueError("transactions must be a list of dicts")

    # -------------------------------
    # JSON-safe sample (PROMPT SAFETY)
    # -------------------------------
    safe_txn = make_json_safe(transactions[:15])

    # -------------------------------
    # Prompt
    # -------------------------------
    prompt = f"""
{SYSTEM_PROMPT}

TRANSACTION_SAMPLE (PATTERN ONLY):
{json.dumps(safe_txn, indent=2)}

Answer:
1. Any unusual timing or clustering?
2. Any high-level behavioral patterns?

Do NOT invent numbers.
"""

    # -------------------------------
    # LLM Call (via shared utility)
    # -------------------------------
    try:
        content = call_llm(
            prompt,
            temperature=0.25
        )

        return {
            "type": "llm_transaction_patterns",
            "model": LLM_MODEL,
            "content": content
        }

    except Exception:
        return {
            "type": "llm_transaction_patterns",
            "model": None,
            "content": (
                "Transaction pattern analysis unavailable.\n"
                "Underlying transaction data remains valid."
            )
        }
