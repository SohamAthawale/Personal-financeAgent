# agent/insights/category_insights.py

import json
import hashlib
from typing import Any, Dict, List
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

CACHE_FILE = CACHE_DIR / "category_insights.json"

# ==================================================
# SYSTEM PROMPT (CONSTRAINED, NON-NUMERIC)
# ==================================================
SYSTEM_PROMPT = """
You are a spending category analyst.

STRICT RULES:
- Use category totals ONLY
- Do NOT infer transactions
- Do NOT invent numbers
- Identify dominant categories and risk
"""


# ==================================================
# HELPERS
# ==================================================
def _fingerprint_categories(
    category_summary: List[Dict[str, Any]]
) -> str:
    """
    Stable fingerprint based on category + amount only.
    """
    minimal = [
        {
            "category": c.get("category"),
            "amount": c.get("amount_out") or c.get("expense"),
        }
        for c in category_summary
    ]

    blob = json.dumps(
        minimal,
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
# CATEGORY INSIGHT GENERATOR (BACKEND ONLY)
# ==================================================
def generate_category_insights(
    category_summary: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Generates qualitative category-level insights.

    Guarantees:
    - Uses cached insights if unchanged
    - Incrementally updates insight on category changes
    - Category totals remain authoritative
    """

    # -------------------------------
    # Hard guards
    # -------------------------------
    if not LLM_ENABLED:
        return {
            "type": "llm_category_insight",
            "model": None,
            "content": "LLM disabled by server configuration.",
            "cached": False,
        }

    if not isinstance(category_summary, list):
        raise ValueError("category_summary must be a list of dicts")

    if not category_summary:
        return {
            "type": "llm_category_insight",
            "model": None,
            "content": "No category data available for insight generation.",
            "cached": False,
        }

    # -------------------------------
    # Fingerprint + cache lookup
    # -------------------------------
    fingerprint = _fingerprint_categories(category_summary)
    cache = _load_cache()

    if cache and cache.get("fingerprint") == fingerprint:
        return {
            "type": "llm_category_insight",
            "model": cache.get("model"),
            "content": cache.get("content"),
            "cached": True,
        }

    # -------------------------------
    # Delta detection
    # -------------------------------
    previous_summary = cache.get("category_summary") if cache else None
    previous_content = cache.get("content") if cache else None

    safe_summary = make_json_safe(category_summary)

    # -------------------------------
    # Prompt (delta-aware)
    # -------------------------------
    if previous_summary and previous_content:
        prompt = f"""
{SYSTEM_PROMPT}

PREVIOUS_INSIGHT:
{previous_content}

UPDATED_CATEGORY_TOTALS:
{json.dumps(safe_summary, indent=2)}

Update the insight only if category dominance,
risk profile, or discretionary mix has changed.
If not, explicitly state that spending structure is stable.

Do NOT invent numbers.
"""
    else:
        prompt = f"""
{SYSTEM_PROMPT}

CATEGORY_TOTALS:
{json.dumps(safe_summary, indent=2)}

Provide:
1. Top spending categories
2. Which categories are discretionary vs fixed
3. One practical optimization suggestion

Do NOT invent numbers.
If unsure, restate the provided totals.
"""

    # -------------------------------
    # LLM Call
    # -------------------------------
    try:
        content = call_llm(
            prompt,
            temperature=0.15
        )

        payload = {
            "fingerprint": fingerprint,
            "category_summary": category_summary,
            "model": LLM_MODEL,
            "content": content,
        }

        _save_cache(payload)

        return {
            "type": "llm_category_insight",
            "model": LLM_MODEL,
            "content": content,
            "cached": False,
        }

    except Exception:
        return {
            "type": "llm_category_insight",
            "model": None,
            "content": (
                "Category insights unavailable.\n"
                "Category totals remain accurate."
            ),
            "cached": False,
        }
