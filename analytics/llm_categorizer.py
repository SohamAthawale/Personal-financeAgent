# analytics/llm_categorizer.py

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
# ALLOWED OUTPUT SPACE (STRICT)
# ==================================================
ALLOWED_CATEGORIES = [
    "Food",
    "Transport",
    "Shopping",
    "Bills",
    "Subscriptions",
    "Medical",
    "Rent",
    "Transfer",
    "Other"
]


# ==================================================
# SYSTEM PROMPT (CONSTRAINED)
# ==================================================
SYSTEM_PROMPT = """
You are a financial transaction categorizer.

Rules:
- Choose exactly ONE category
- Use merchant name primarily
- Be conservative
- Prefer Other if uncertain
- Output ONLY valid JSON
"""


# ==================================================
# LLM CATEGORIZATION (BACKEND ONLY)
# ==================================================
@lru_cache(maxsize=1024)
def llm_categorize_merchant(merchant: str) -> tuple[str, float]:
    """
    Backend-only semantic categorization.
    Returns: (category, confidence)

    - Deterministic fallback if LLM disabled
    - Constrained output space
    - Cached for performance
    """

    # -------------------------------
    # Hard guards
    # -------------------------------
    if not merchant:
        return "Other", 0.0

    if not LLM_ENABLED:
        return "Other", 0.0

    # -------------------------------
    # Prompt
    # -------------------------------
    prompt = f"""
{SYSTEM_PROMPT}

Allowed categories:
{ALLOWED_CATEGORIES}

Merchant:
"{merchant}"

Output:
{{ "category": "...", "confidence": 0.0 }}
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
            timeout=20
        )

        resp.raise_for_status()

        raw = resp.json().get("response", "")

        # -------------------------------
        # Strict JSON extraction
        # -------------------------------
        start, end = raw.find("{"), raw.rfind("}") + 1
        if start == -1 or end == -1:
            return "Other", 0.0

        data = json.loads(raw[start:end])

        category = data.get("category", "Other")
        confidence = float(data.get("confidence", 0.0))

        # -------------------------------
        # Output validation
        # -------------------------------
        if category not in ALLOWED_CATEGORIES:
            return "Other", 0.0

        confidence = max(0.0, min(confidence, 1.0))

        return category, confidence

    except Exception:
        # Fail-safe: never break pipeline
        return "Other", 0.0
