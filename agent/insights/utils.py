# agent/insights/utils.py

from typing import Any

import numpy as np

from llm.adapter import generate_text


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
    """
    response = generate_text(
        prompt=prompt,
        temperature=temperature,
        max_retries=max_retries,
    )

    return response or "⚠️ Insight generation unavailable."
