# analytics/llm_name_classifier.py

import json
import requests
from functools import lru_cache

# ==================================================
# BACKEND CONFIG (NO HARDCODED VALUES)
# ==================================================
try:
    from config.llm import LLM_ENABLED, OLLAMA_URL, LLM_MODEL
except ImportError:
    # Safe defaults if config not present
    LLM_ENABLED = True
    OLLAMA_URL = "http://localhost:11434/api/generate"
    LLM_MODEL = "llama3"


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

    if not LLM_ENABLED:
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
        resp = requests.post(
            OLLAMA_URL,
            json={
                "model": LLM_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.0,   # 🔒 deterministic
                    "top_p": 1.0
                }
            },
            timeout=15
        )

        resp.raise_for_status()

        raw = resp.json().get("response", "")

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
