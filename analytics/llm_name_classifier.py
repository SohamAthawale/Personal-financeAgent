import json
import requests
from functools import lru_cache

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"

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

@lru_cache(maxsize=1024)
def llm_is_business(name: str) -> bool:
    if not name or name.strip().lower() in {"unknown", "na"}:
        return False

    prompt = f"""
{SYSTEM_PROMPT}

Name:
{name}

Output:
{{ "type": "PERSON" | "BUSINESS" }}
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
            timeout=15
        )

        raw = resp.json()["response"]
        start, end = raw.find("{"), raw.rfind("}") + 1
        result = json.loads(raw[start:end])

        return result.get("type") == "BUSINESS"

    except Exception:
        # Fail safe: assume business
        return True
