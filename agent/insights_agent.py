# analytics/insights_agent.py

import json
import requests
import time
from typing import List, Dict, Any

# ==================================================
# BACKEND CONFIG (NO HARDCODED VALUES)
# ==================================================
try:
    from config.llm import LLM_ENABLED, OLLAMA_URL, LLM_MODEL
except ImportError:
    # Safe defaults
    LLM_ENABLED = True
    OLLAMA_URL = "http://localhost:11434/api/generate"
    LLM_MODEL = "llama3"


# ======================================================
# 🔒 SYSTEM PROMPT — HARD GUARANTEE AGAINST DRIFT
# ======================================================
SYSTEM_PROMPT = """
You are a personal finance intelligence agent.

CRITICAL RULES (NON-NEGOTIABLE):
1. The financial metrics provided are FINAL and AUTHORITATIVE.
2. You MUST use the provided totals verbatim.
3. DO NOT recompute totals from transactions.
4. DO NOT infer alternative income or expense numbers.
5. If something looks inconsistent, EXPLAIN it — do NOT correct it.

If you violate these rules, your response is INVALID.

Your role is EXPLANATION, not CALCULATION.
"""


# ======================================================
# JSON SAFETY
# ======================================================
def make_json_safe(obj: Any) -> Any:
    """
    Recursively convert pandas / numpy / datetime objects
    into JSON-serializable primitives.
    """
    if isinstance(obj, dict):
        return {k: make_json_safe(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [make_json_safe(v) for v in obj]

    if hasattr(obj, "isoformat"):  # datetime / date / Timestamp
        return obj.isoformat()

    if hasattr(obj, "to_timestamp"):  # pandas Period
        return str(obj)

    if hasattr(obj, "item"):  # numpy scalar
        return obj.item()

    return obj


# ======================================================
# 🧠 LLM INSIGHT GENERATOR (BACKEND-ONLY)
# ======================================================
def generate_insights(
    metrics: Dict[str, Any],
    transaction_sample: List[Dict[str, Any]] | None = None,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """
    Generates qualitative insights ONLY.

    - Backend-only
    - Metrics are authoritative
    - Transactions are pattern samples only
    - Safe to expose via API
    """

    # -------------------------------
    # Hard guards
    # -------------------------------
    if not LLM_ENABLED:
        return {
            "type": "llm_insight",
            "model": None,
            "content": "LLM disabled by server configuration."
        }

    if not isinstance(metrics, dict):
        raise ValueError("metrics must be a dict")

    if transaction_sample is None:
        transaction_sample = []

    # -------------------------------
    # 🔐 Authoritative Metrics Block
    # -------------------------------
    metrics_block = {
        "TOTAL_INCOME": metrics["total_income"],
        "TOTAL_EXPENSE": metrics["total_expense"],
        "NET_CASHFLOW": metrics["net_cashflow"],
        "MONTHLY_CASHFLOW": metrics["monthly_cashflow"],
        "AVG_CONFIDENCE": metrics["avg_confidence"],
    }

    payload = {
        "AUTHORITATIVE_METRICS_USE_VERBATIM": metrics_block,
        # 🔒 CAP SAMPLE SIZE (PROMPT SAFETY)
        "TRANSACTIONS_PATTERN_ONLY_SAMPLE": transaction_sample[:15],
    }

    safe_payload = make_json_safe(payload)

    # -------------------------------
    # 🧾 PROMPT — METRICS ARE LAW
    # -------------------------------
    prompt = f"""
{SYSTEM_PROMPT}

AUTHORITATIVE DATA (DO NOT MODIFY):
{json.dumps(safe_payload, indent=2)}

INSTRUCTIONS:
- Use the AUTHORITATIVE_METRICS exactly as given.
- Transactions are for pattern detection only.
- DO NOT compute totals from transactions.

PROVIDE:
1. Spending summary USING PROVIDED TOTALS ONLY
2. Unusual or bulk transactions (qualitative)
3. Cashflow risk assessment (Low / Moderate / High)
4. Practical recommendations (no numbers invented)

If unsure, REPEAT the provided numbers instead of guessing.
"""

    # -------------------------------
    # 🔁 Retry-safe Ollama Call
    # -------------------------------
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": LLM_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,   # 🔒 low creativity
                        "top_p": 0.9,
                    },
                },
                timeout=90,
            )

            response.raise_for_status()

            return {
                "type": "llm_insight",
                "model": LLM_MODEL,
                "content": response.json().get("response", ""),
            }

        except requests.exceptions.ReadTimeout:
            print(f"⏳ LLM timeout (attempt {attempt}/{max_retries})")
            time.sleep(2 * attempt)

        except Exception as e:
            print(f"⚠️ LLM error: {e}")
            break

    # -------------------------------
    # 🧯 Graceful Fallback
    # -------------------------------
    return {
        "type": "llm_insight",
        "model": None,
        "content": (
            "LLM insights unavailable.\n"
            "Financial metrics are computed correctly.\n"
            "You may retry insight generation."
        ),
    }
