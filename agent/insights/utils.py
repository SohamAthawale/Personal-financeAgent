# agent/insights/utils.py

import json
import requests
import time
from typing import Any

# ==================================================
# BACKEND CONFIG (SINGLE SOURCE OF TRUTH)
# ==================================================
try:
    from config.llm import LLM_ENABLED, OLLAMA_URL, LLM_MODEL
except ImportError:
    # Safe defaults (local dev)
    LLM_ENABLED = True
    OLLAMA_URL = "http://localhost:11434/api/generate"
    LLM_MODEL = "llama3"


# ==================================================
# JSON SAFETY
# ==================================================
def make_json_safe(obj: Any) -> Any:
    """
    Recursively convert pandas / numpy / datetime objects
    into JSON-serializable primitives.
    """
    if isinstance(obj, dict):
        return {k: make_json_safe(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [make_json_safe(v) for v in obj]

    if hasattr(obj, "isoformat"):
        return obj.isoformat()

    if hasattr(obj, "to_timestamp"):
        return str(obj)

    if hasattr(obj, "item"):
        return obj.item()

    return obj


# ==================================================
# SHARED LLM CALL (BACKEND ONLY)
# ==================================================
def call_llm(
    prompt: str,
    temperature: float = 0.1,
    max_retries: int = 3,
) -> str:
    """
    Centralized LLM call utility.

    - Backend-only
    - Controlled retries
    - Deterministic-friendly
    - Safe fallback
    """

    # -------------------------------
    # Hard guard
    # -------------------------------
    if not LLM_ENABLED:
        return "LLM disabled by server configuration."

    # -------------------------------
    # Retry-safe call
    # -------------------------------
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": LLM_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": float(temperature),
                        "top_p": 0.9,
                    },
                },
                timeout=90,
            )

            response.raise_for_status()

            return response.json().get("response", "")

        except requests.exceptions.ReadTimeout:
            print(f"⏳ LLM timeout ({attempt}/{max_retries})")
            time.sleep(2 * attempt)

        except Exception as e:
            print(f"⚠️ LLM error: {e}")
            break

    # -------------------------------
    # Graceful fallback
    # -------------------------------
    return "⚠️ Insight generation unavailable."
