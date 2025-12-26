import json
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"

SYSTEM_PROMPT = """
You are a financial statement schema judge.

You do NOT extract data.
You ONLY decide which schema interpretation is most plausible.

Rules:
- Prefer accounting-consistent interpretations
- Prefer realistic bank layouts
- Output ONLY valid JSON
- No explanations
"""

def llm_arbitrate(candidates):
    """
    candidates = list of dicts:
    {
        "schema": {...},
        "confidence": 0.78,
        "variant": "drop_first_3"
    }
    """

    prompt = f"""
{SYSTEM_PROMPT}

Candidates:
{json.dumps(candidates, indent=2)}

Choose the best schema.

Output JSON:
{{ "winner_index": number }}
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
            timeout=30
        )

        raw = resp.json()["response"]
        start, end = raw.find("{"), raw.rfind("}") + 1
        result = json.loads(raw[start:end])

        idx = result.get("winner_index")
        if idx is None or idx >= len(candidates):
            return None

        return candidates[idx]

    except Exception:
        return None
