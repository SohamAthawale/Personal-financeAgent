# config/llm.py
import os

# Master switch (used by backend only)
LLM_ENABLED = os.getenv("LLM_ENABLED", "true").lower() == "true"

# Ollama connection
OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://localhost:11434/api/generate"
)

# Model name
LLM_MODEL = os.getenv(
    "LLM_MODEL",
    "qwen2.5:7b"
)
