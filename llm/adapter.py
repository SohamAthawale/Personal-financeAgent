import time
from datetime import datetime
from threading import Lock
from typing import Optional

import requests

try:
    from config.llm import (
        LLM_ENABLED,
        LLM_PROVIDER,
        OLLAMA_URL,
        LLM_MODEL,
        OPENAI_API_KEY,
        OPENAI_BASE_URL,
        OPENAI_ORG,
        OPENAI_PROJECT,
    )
except ImportError:
    # Safe defaults (local dev)
    LLM_ENABLED = True
    LLM_PROVIDER = "ollama"
    OLLAMA_URL = "http://localhost:11434/api/generate"
    LLM_MODEL = "llama3"
    OPENAI_API_KEY = None
    OPENAI_BASE_URL = "https://api.openai.com/v1"
    OPENAI_ORG = None
    OPENAI_PROJECT = None

# ==================================================
# INTERNAL STATE
# ==================================================
_LLM_LOCK = Lock()
_LAST_FAILURE_TS = 0.0
_FAILURE_COOLDOWN = 30  # seconds


def is_llm_enabled() -> bool:
    return bool(LLM_ENABLED)


def _guard_prompt(prompt: str, max_chars: int) -> str:
    if len(prompt) <= max_chars:
        return prompt
    return prompt[:max_chars] + "\n\n[TRUNCATED FOR SAFETY]"


def _call_ollama(
    prompt: str,
    temperature: float,
    top_p: float,
    timeout: int,
    model: str,
) -> str:
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": float(temperature),
                "top_p": float(top_p),
            },
        },
        timeout=timeout,
    )

    response.raise_for_status()
    return response.json().get("response", "")


def _call_openai_compatible(
    prompt: str,
    temperature: float,
    top_p: float,
    timeout: int,
    model: str,
) -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")

    url = OPENAI_BASE_URL.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    if OPENAI_ORG:
        headers["OpenAI-Organization"] = OPENAI_ORG
    if OPENAI_PROJECT:
        headers["OpenAI-Project"] = OPENAI_PROJECT

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": float(temperature),
        "top_p": float(top_p),
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=timeout,
    )

    response.raise_for_status()
    data = response.json()

    choices = data.get("choices", [])
    if not choices:
        return ""

    message = choices[0].get("message", {})
    return message.get("content", "")


def generate_text(
    prompt: str,
    temperature: float = 0.1,
    max_retries: int = 3,
    timeout: int = 60,
    top_p: float = 0.9,
    max_prompt_chars: int = 12_000,
    return_none_on_fail: bool = False,
    model: str | None = None,
) -> Optional[str]:
    """
    Centralized LLM call utility.

    Guarantees:
    - Single-flight protection (per process)
    - Controlled retries
    - Circuit breaker on repeated failure
    """

    global _LAST_FAILURE_TS

    if not LLM_ENABLED:
        return None if return_none_on_fail else "LLM disabled by server configuration."

    now = time.time()
    if now - _LAST_FAILURE_TS < _FAILURE_COOLDOWN:
        return None if return_none_on_fail else "⚠️ LLM temporarily unavailable. Using cached insights."

    prompt = _guard_prompt(prompt, max_prompt_chars)

    with _LLM_LOCK:
        for attempt in range(1, max_retries + 1):
            try:
                provider = (LLM_PROVIDER or "ollama").lower()
                selected_model = model or LLM_MODEL

                if provider == "ollama":
                    return _call_ollama(
                        prompt,
                        temperature,
                        top_p,
                        timeout,
                        selected_model,
                    )

                if provider in {"openai", "openai_compatible"}:
                    return _call_openai_compatible(
                        prompt,
                        temperature,
                        top_p,
                        timeout,
                        selected_model,
                    )

                raise RuntimeError(f"Unknown LLM_PROVIDER: {provider}")

            except requests.exceptions.ReadTimeout:
                print(f"⏳ LLM timeout ({attempt}/{max_retries})")
                time.sleep(2 * attempt)

            except Exception as e:
                print(f"⚠️ LLM error: {e}")
                _LAST_FAILURE_TS = time.time()
                break

    return None if return_none_on_fail else "⚠️ Insight generation unavailable."


def check_llm_health(
    *,
    timeout: int = 5,
    model: str | None = None,
) -> dict:
    """
    Lightweight health check for the configured LLM.
    Returns a structured status payload for UI consumption.
    """
    checked_at = datetime.utcnow().isoformat()
    provider = (LLM_PROVIDER or "unknown").lower()
    selected_model = model or LLM_MODEL

    if not LLM_ENABLED:
        return {
            "status": "disabled",
            "message": "LLM disabled by server configuration.",
            "provider": provider,
            "model": selected_model,
            "checked_at": checked_at,
        }

    try:
        response = generate_text(
            prompt="ping",
            temperature=0.0,
            top_p=1.0,
            timeout=timeout,
            max_retries=1,
            return_none_on_fail=True,
            model=selected_model,
        )

        if response:
            return {
                "status": "ok",
                "provider": provider,
                "model": selected_model,
                "checked_at": checked_at,
            }

        return {
            "status": "unavailable",
            "message": "LLM call failed or timed out.",
            "provider": provider,
            "model": selected_model,
            "checked_at": checked_at,
        }

    except Exception as exc:
        return {
            "status": "error",
            "message": str(exc),
            "provider": provider,
            "model": selected_model,
            "checked_at": checked_at,
        }
