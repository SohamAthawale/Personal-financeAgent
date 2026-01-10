# agent/insights/financial_summary.py

import json
import hashlib
from typing import Any, Dict
from pathlib import Path

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
# CACHE CONFIG
# ==================================================
CACHE_DIR = Path(".cache/insights")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

CACHE_FILE = CACHE_DIR / "financial_summary.json"

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
# HELPERS
# ==================================================
def _fingerprint_metrics(metrics: Dict[str, Any]) -> str:
    """
    Stable fingerprint of authoritative metrics.
    """
    blob = json.dumps(
        metrics,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(blob.encode()).hexdigest()


def _load_cache() -> Dict[str, Any] | None:
    if not CACHE_FILE.exists():
        return None
    try:
        return json.loads(CACHE_FILE.read_text())
    except Exception:
        return None


def _save_cache(payload: Dict[str, Any]) -> None:
    CACHE_FILE.write_text(json.dumps(payload, indent=2))


# ==================================================
# FINANCIAL SUMMARY GENERATOR (BACKEND ONLY)
# ==================================================
def generate_financial_summary(
    metrics: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generates a qualitative financial summary.

    Guarantees:
    - Metrics are authoritative
    - Cached if unchanged
    - No delta reasoning
    - Deterministic & auditable
    """

    # -------------------------------
    # Hard guards
    # -------------------------------
    if not LLM_ENABLED:
        return {
            "type": "llm_financial_summary",
            "model": None,
            "content": "LLM disabled by server configuration.",
            "cached": False,
        }

    if not isinstance(metrics, dict):
        raise ValueError("metrics must be a dict")

    if not metrics:
        return {
            "type": "llm_financial_summary",
            "model": None,
            "content": "No financial metrics available.",
            "cached": False,
        }

    # -------------------------------
    # Fingerprint + cache lookup
    # -------------------------------
    safe_metrics = make_json_safe(metrics)
    fingerprint = _fingerprint_metrics(safe_metrics)

    cache = _load_cache()
    if cache and cache.get("fingerprint") == fingerprint:
        return {
            "type": "llm_financial_summary",
            "model": cache.get("model"),
            "content": cache.get("content"),
            "cached": True,
        }

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
    # LLM Call
    # -------------------------------
    try:
        content = call_llm(
            prompt,
            temperature=0.05
        )

        payload = {
            "fingerprint": fingerprint,
            "metrics": safe_metrics,
            "model": LLM_MODEL,
            "content": content,
        }

        _save_cache(payload)

        return {
            "type": "llm_financial_summary",
            "model": LLM_MODEL,
            "content": content,
            "cached": False,
        }

    except Exception:
        return {
            "type": "llm_financial_summary",
            "model": None,
            "content": (
                "Financial summary unavailable.\n"
                "Authoritative metrics remain valid."
            ),
            "cached": False,
        }
