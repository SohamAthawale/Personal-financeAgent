import json
import requests
import time

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"


def make_json_safe(obj):
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


def call_llm(prompt, temperature=0.1, max_retries=3):
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "top_p": 0.9
                    }
                },
                timeout=90
            )
            response.raise_for_status()
            return response.json()["response"]

        except requests.exceptions.ReadTimeout:
            print(f"⏳ LLM timeout ({attempt}/{max_retries})")
            time.sleep(2 * attempt)

    return "⚠️ Insight generation unavailable."
