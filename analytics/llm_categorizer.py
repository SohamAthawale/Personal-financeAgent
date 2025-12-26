# analytics/llm_categorizer.py

import json
import requests
from functools import lru_cache

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"

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

SYSTEM_PROMPT = """
You are a financial transaction categorizer.

Rules:
- Choose exactly ONE category
- Use merchant name primarily
- Be conservative
- Prefer Other if uncertain
- Output ONLY valid JSON
"""

@lru_cache(maxsize=1024)
def llm_categorize_merchant(merchant: str) -> tuple[str, float]:
    if not merchant:
        return "Other", 0.0

    prompt = f"""
{SYSTEM_PROMPT}

Allowed categories:
{ALLOWED_CATEGORIES}

Merchant:
"{merchant}"

Output:
{{ "category": "...", "confidence": 0.0 }}
"""

    try:
        resp = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0}
            },
            timeout=20
        )

        raw = resp.json()["response"]
        data = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])

        category = data.get("category", "Other")
        confidence = float(data.get("confidence", 0))

        if category not in ALLOWED_CATEGORIES:
            return "Other", 0.0

        return category, confidence

    except Exception:
        return "Other", 0.0
