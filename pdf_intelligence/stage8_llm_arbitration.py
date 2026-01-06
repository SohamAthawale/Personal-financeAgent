# pdf_intelligence/stage8_llm_arbitration.py

import json
import requests
from typing import List, Dict, Any

# ==================================================
# BACKEND CONFIG (NO HARDCODED VALUES)
# ==================================================
try:
    from config.llm import LLM_ENABLED, OLLAMA_URL, LLM_MODEL
except ImportError:
    # Safe defaults
    LLM_ENABLED = True
    OLLAMA_URL = "http://localhost:11434/api/generate"
    LLM_MODEL = "llama3"


# ==================================================
# SYSTEM PROMPT (STRICT, NON-GENERATIVE)
# ==================================================
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


# ==================================================
# LLM ARBITRATION (BACKEND ONLY)
# ==================================================
def llm_arbitrate(
    candidates: List[Dict[str, Any]]
) -> Dict[str, Any] | None:
    """
    Selects the best schema candidate using constrained LLM arbitration.

    candidates = [
        {
            "schema": {...},
            "confidence": 0.78,
            "variant": "drop_first_3"
        },
        ...
    ]

    Returns:
        - winning candidate dict
        - None if arbitration fails or is disabled
    """

    # -------------------------------
    # Hard guards
    # -------------------------------
    if not LLM_ENABLED:
        return None

    if not candidates or len(candidates) < 2:
        return None

    # -------------------------------
    # Prompt
    # -------------------------------
    prompt = f"""
{SYSTEM_PROMPT}

Candidates:
{json.dumps(candidates, indent=2)}

Choose the best schema.

Output JSON:
{{ "winner_index": number }}
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
                    "temperature": 0.0,  # 🔒 deterministic
                    "top_p": 1.0
                },
            },
            timeout=30,
        )

        resp.raise_for_status()

        raw = resp.json().get("response", "")

        # -------------------------------
        # Strict JSON extraction
        # -------------------------------
        start, end = raw.find("{"), raw.rfind("}") + 1
        if start == -1 or end == -1:
            return None

        result = json.loads(raw[start:end])

        idx = result.get("winner_index")

        if not isinstance(idx, int):
            return None

        if idx < 0 or idx >= len(candidates):
            return None

        return candidates[idx]

    except Exception:
        # Fail-safe: deterministic pipeline continues
        return None
