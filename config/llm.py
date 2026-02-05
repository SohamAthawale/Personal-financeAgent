# config/llm.py
import os

# Master switch (used by backend only)
LLM_ENABLED = os.getenv("LLM_ENABLED", "true").lower() == "true"

# Provider: ollama | openai_compatible
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()

# Ollama connection
OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://localhost:11434/api/generate"
)

# Model name
LLM_MODEL = os.getenv(
    "LLM_MODEL",
    "qwen2.5:7b-instruct"
)

# OpenAI-compatible settings (used when LLM_PROVIDER=openai_compatible)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_ORG = os.getenv("OPENAI_ORG")
OPENAI_PROJECT = os.getenv("OPENAI_PROJECT")
