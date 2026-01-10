# agent/insights/utils.py

import json
import numpy as np
import requests
import time
from typing import Any
from threading import Lock

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
# INTERNAL STATE
# ==================================================
_LLM_LOCK = Lock()
_LAST_FAILURE_TS = 0.0
_FAILURE_COOLDOWN = 30  # seconds


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

    # datetime, pandas Timestamp
    if hasattr(obj, "isoformat"):
        return obj.isoformat()

    # pandas Period, etc.
    if hasattr(obj, "to_timestamp"):
        return str(obj)

    # numpy scalar
    if isinstance(obj, np.generic):
        return obj.item()

    # pandas scalar
    if hasattr(obj, "item"):
        try:
            return obj.item()
        except Exception:
            pass

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

    Guarantees:
    - Single-flight protection (per process)
    - Controlled retries
    - Circuit breaker on repeated failure
    - Deterministic-friendly
    """

    global _LAST_FAILURE_TS

    # -------------------------------
    # Hard guards
    # -------------------------------
    if not LLM_ENABLED:
        return "LLM disabled by server configuration."

    now = time.time()
    if now - _LAST_FAILURE_TS < _FAILURE_COOLDOWN:
        return "⚠️ LLM temporarily unavailable. Using cached insights."

    # Prevent pathological prompts
    if len(prompt) > 12_000:
        prompt = prompt[:12_000] + "\n\n[TRUNCATED FOR SAFETY]"

    # -------------------------------
    # Single-flight lock
    # -------------------------------
    with _LLM_LOCK:
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
                    timeout=60,
                )

                response.raise_for_status()

                return response.json().get("response", "")

            except requests.exceptions.ReadTimeout:
                print(f"⏳ LLM timeout ({attempt}/{max_retries})")
                time.sleep(2 * attempt)

            except Exception as e:
                print(f"⚠️ LLM error: {e}")
                _LAST_FAILURE_TS = time.time()
                break

    # -------------------------------
    # Graceful fallback
    # -------------------------------
    return "⚠️ Insight generation unavailable."
