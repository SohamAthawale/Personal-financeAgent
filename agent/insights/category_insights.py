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

FAILURE_MARKER = "Category insights unavailable"

# ==================================================
# SYSTEM PROMPT
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
    minimal = [
        {
            "category": c.get("category"),
            "amount": float(
                c.get("amount_out")
                if c.get("amount_out") is not None
                else c.get("expense", 0.0)
            ),
        }
        for c in category_summary
    ]

    safe_minimal = make_json_safe(minimal)

    blob = json.dumps(
        safe_minimal,
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
# CATEGORY INSIGHT GENERATOR
# ==================================================
def generate_category_insights(
    category_summary: List[Dict[str, Any]]
) -> Dict[str, Any]:

    if not LLM_ENABLED:
        return {
            "type": "llm_category_insight",
            "model": None,
            "content": "LLM disabled by server configuration.",
            "cached": False,
        }

    if not isinstance(category_summary, list):
        raise ValueError("category_summary must be a list")

    if not category_summary:
        return {
            "type": "llm_category_insight",
            "model": None,
            "content": "No category data available.",
            "cached": False,
        }

    fingerprint = _fingerprint_categories(category_summary)
    cache = _load_cache()

    cached_content = None
    cached_model = None

    # --------------------------------------------------
    # Cache usage (SUCCESS ONLY)
    # --------------------------------------------------
    if cache and cache.get("fingerprint") == fingerprint:
        cached_content = cache.get("content")
        cached_model = cache.get("model")

        if cached_content and FAILURE_MARKER not in cached_content:
            return {
                "type": "llm_category_insight",
                "model": cached_model,
                "content": cached_content,
                "cached": True,
            }
        # else → retry LLM

    # --------------------------------------------------
    # Prompt (delta-aware)
    # --------------------------------------------------
    safe_summary = make_json_safe(category_summary)

    previous_content = (
        cache.get("content")
        if cache and FAILURE_MARKER not in (cache.get("content") or "")
        else None
    )

    if previous_content:
        prompt = f"""
{SYSTEM_PROMPT}

PREVIOUS_INSIGHT:
{previous_content}

UPDATED_CATEGORY_TOTALS:
{json.dumps(safe_summary, indent=2)}

Update insight ONLY if structure changed.
If unchanged, explicitly say so.

Do NOT invent numbers.
"""
    else:
        prompt = f"""
{SYSTEM_PROMPT}

CATEGORY_TOTALS:
{json.dumps(safe_summary, indent=2)}

Provide:
1. Top spending categories
2. Fixed vs discretionary split
3. One optimization suggestion

Do NOT invent numbers.
"""

    # --------------------------------------------------
    # LLM Call (SELF-HEALING)
    # --------------------------------------------------
    try:
        content = call_llm(prompt, temperature=0.15)

        payload = {
            "fingerprint": fingerprint,
            "category_summary": safe_summary,
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
        # 🔥 FALLBACK TO CACHE IF AVAILABLE
        if cached_content:
            return {
                "type": "llm_category_insight",
                "model": cached_model,
                "content": cached_content,
                "cached": True,
            }

        return {
            "type": "llm_category_insight",
            "model": None,
            "content": f"{FAILURE_MARKER}.",
            "cached": False,
        }
