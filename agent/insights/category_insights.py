# agent/insights/category_insights.py

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
# CATEGORY INSIGHT GENERATOR (BACKEND ONLY)
# ==================================================
def generate_category_insights(
    category_summary: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Generates qualitative category-level insights.

    - Backend-only
    - Category totals are authoritative
    - Safe to expose via API
    """

    # -------------------------------
    # Hard guards
    # -------------------------------
    if not LLM_ENABLED:
        return {
            "type": "llm_category_insight",
            "model": None,
            "content": "LLM disabled by server configuration."
        }

    if not isinstance(category_summary, list):
        raise ValueError("category_summary must be a list of dicts")

    # -------------------------------
    # JSON-safe input
    # -------------------------------
    safe_summary = make_json_safe(category_summary)

    # -------------------------------
    # Prompt
    # -------------------------------
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
    # LLM Call (via shared utility)
    # -------------------------------
    try:
        content = call_llm(
            prompt,
            temperature=0.15
        )

        return {
            "type": "llm_category_insight",
            "model": LLM_MODEL,
            "content": content
        }

    except Exception:
        return {
            "type": "llm_category_insight",
            "model": None,
            "content": (
                "Category insights unavailable.\n"
                "Category totals remain accurate."
            )
        }
