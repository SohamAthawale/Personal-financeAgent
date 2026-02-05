# analytics/llm_name_classifier.py

import json
import re
from functools import lru_cache

from llm.adapter import generate_text, is_llm_enabled


# ==================================================
# SYSTEM PROMPT (STRICT & CONSTRAINED)
# ==================================================
SYSTEM_PROMPT = """
You are a strict financial name classifier.

Your task:
Given a merchant name from a bank statement,
decide whether it represents:

- a PERSON (individual human)
- a BUSINESS (shop, company, service, organization)

Rules:
- Names like "RAJEEV KUMAR", "ARUNDHATI CHAIT" → PERSON
- Names like "LIFESTYLE", "S R ENTERPRISES", "KASTUR VIHAR" → BUSINESS
- If unsure, prefer BUSINESS

Output ONLY valid JSON.
No explanation.
"""


# ==================================================
# LLM NAME CLASSIFIER (BACKEND ONLY)
# ==================================================
@lru_cache(maxsize=1024)
def llm_is_business(name: str) -> bool:
    """
    Backend-only semantic classifier.
    Returns True if BUSINESS, False if PERSON.

    - Deterministic fallback
    - Cached
    - Fail-safe (finance-safe)
    """

    # -------------------------------
    # Hard guards
    # -------------------------------
    if not name or name.strip().lower() in {"unknown", "na"}:
        return False

    if not is_llm_enabled():
        # Conservative default in finance
        return True

    # -------------------------------
    # Prompt
    # -------------------------------
    prompt = f"""
{SYSTEM_PROMPT}

Name:
{name}

Output:
{{ "type": "PERSON" | "BUSINESS" }}
"""

    # -------------------------------
    # LLM Call
    # -------------------------------
    try:
        raw = generate_text(
            prompt=prompt,
            temperature=0.0,
            top_p=1.0,
            timeout=15,
            return_none_on_fail=True,
            model="qwen2.5:1.5b",
        )

        if not raw:
            return True  # finance-safe default

        # -------------------------------
        # Strict JSON extraction
        # -------------------------------
        start, end = raw.find("{"), raw.rfind("}") + 1
        if start == -1 or end == -1:
            return True  # finance-safe default

        result = json.loads(raw[start:end])

        return result.get("type") == "BUSINESS"

    except Exception:
        # Fail-safe: assume BUSINESS
        return True


# ==================================================
# 🔥 ADDITIONS BELOW (NO EXISTING CODE MODIFIED)
# ==================================================

# ---- NEW: deterministic heuristics (fast & free) ----

PERSON_NAME_RX = re.compile(
    r"^[A-Z][a-z]+(\s+[A-Z][a-z]+){0,2}$"
)

BUSINESS_KEYWORDS = {
    "store", "shop", "mart", "hotel", "restaurant", "cafe",
    "enterprise", "enterprises", "traders", "services",
    "foods", "food", "medical", "pharmacy", "chemist",
    "limited", "ltd", "pvt", "private", "company", "co",
}

def heuristic_is_business(name: str) -> tuple[bool | None, float]:
    """
    Cheap deterministic classifier.
    Returns (is_business, confidence) or (None, 0.0)
    """
    if not name:
        return None, 0.0

    n = name.lower().strip()

    for kw in BUSINESS_KEYWORDS:
        if kw in n:
            return True, 0.9

    if PERSON_NAME_RX.match(name.strip()):
        return False, 0.8

    return None, 0.0


# ---- NEW: smart wrapper (heuristics → LLM) ----

def smart_is_business(name: str) -> tuple[bool, float, str]:
    """
    Unified entrypoint for name classification.

    Order:
    1. Heuristic (fast, deterministic)
    2. LLM fallback

    Returns:
    (is_business, confidence, source)
    """

    # 1️⃣ Heuristic short-circuit
    h_result, h_conf = heuristic_is_business(name)
    if h_result is not None:
        return h_result, h_conf, "heuristic"

    # 2️⃣ LLM fallback
    result = llm_is_business(name)
    return result, 0.75, "llm"


# ---- NEW: convenience helpers ----

def is_person(name: str) -> bool:
    """
    Finance-safe helper.
    """
    return not smart_is_business(name)[0]


def name_classification_confidence(name: str) -> float:
    """
    Returns confidence score for classification.
    """
    _, conf, _ = smart_is_business(name)
    return conf
