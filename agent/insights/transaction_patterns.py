# agent/insights/transaction_patterns.py

import json
import hashlib
from typing import Any, Dict, List
from pathlib import Path

# ==================================================
# BACKEND CONFIG
# ==================================================
try:
    from config.llm import LLM_ENABLED, LLM_MODEL
except ImportError:
    LLM_ENABLED = True
    LLM_MODEL = "llama3"

from agent.insights.utils import make_json_safe, call_llm

# ==================================================
# CACHE CONFIG (LOCAL, FAST, SAFE)
# ==================================================
CACHE_DIR = Path(".cache/insights")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

CACHE_FILE = CACHE_DIR / "transaction_patterns.json"

# ==================================================
# SYSTEM PROMPT (STRICT, QUALITATIVE ONLY)
# ==================================================
SYSTEM_PROMPT = """
You are a transaction pattern analyst.

STRICT RULES:
- Transactions are qualitative only
- Do NOT compute totals
- Do NOT invent amounts
- Use words like: frequent, clustered, large, repeated
"""


# ==================================================
# HELPERS
# ==================================================
def _fingerprint_transactions(
    transactions: List[Dict[str, Any]]
) -> str:
    """
    Stable, order-independent fingerprint.
    Sensitive only to meaningful content changes.
    """

    minimal = []
    for t in transactions:
        date_val = t.get("date")

        # 🔒 Convert date/datetime safely
        if hasattr(date_val, "isoformat"):
            date_val = date_val.isoformat()
        elif date_val is not None:
            date_val = str(date_val)

        minimal.append(
            {
                "date": date_val,
                "merchant": t.get("merchant"),
                "amount": float(t.get("amount")) if t.get("amount") is not None else None,
                "category": t.get("category"),
            }
        )

    blob = json.dumps(
        minimal,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(blob.encode()).hexdigest()


def _load_cache() -> Dict[str, Any] | None:
    if not CACHE_FILE.exists():
        return None
    try:
        return json.loads(CACHE_FILE.read_text())
    except Exception:
        return None


def _save_cache(payload: Dict[str, Any]) -> None:
    CACHE_FILE.write_text(json.dumps(payload, indent=2))


# ==================================================
# TRANSACTION PATTERN ANALYZER (BACKEND ONLY)
# ==================================================
def generate_transaction_patterns(
    transactions: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Generates qualitative transaction pattern insights.

    Guarantees:
    - Uses cached insights if data unchanged
    - Uses delta update if data grows
    - Never recomputes unnecessarily
    """

    # -------------------------------
    # Hard guards
    # -------------------------------
    if not LLM_ENABLED:
        return {
            "type": "llm_transaction_patterns",
            "model": None,
            "content": "LLM disabled by server configuration.",
            "cached": False,
        }

    if not isinstance(transactions, list):
        raise ValueError("transactions must be a list of dicts")

    if not transactions:
        return {
            "type": "llm_transaction_patterns",
            "model": None,
            "content": "No transactions available for pattern analysis.",
            "cached": False,
        }

    # -------------------------------
    # Fingerprint + cache lookup
    # -------------------------------
    fingerprint = _fingerprint_transactions(transactions)
    cache = _load_cache()

    if cache and cache.get("fingerprint") == fingerprint:
        return {
            "type": "llm_transaction_patterns",
            "model": cache.get("model"),
            "content": cache.get("content"),
            "cached": True,
        }

    # -------------------------------
    # Delta logic (NEW DATA ONLY)
    # -------------------------------
    previous_content = None
    previous_count = 0

    if cache:
        previous_content = cache.get("content")
        previous_count = cache.get("transaction_count", 0)

    new_txns = transactions[previous_count:]
    safe_new_txns = make_json_safe(new_txns[:15])

    # -------------------------------
    # Prompt (delta-aware)
    # -------------------------------
    if previous_content:
        prompt = f"""
{SYSTEM_PROMPT}

PREVIOUS_INSIGHT:
{previous_content}

NEW_TRANSACTION_SAMPLE (PATTERN ONLY):
{json.dumps(safe_new_txns, indent=2)}

Update the insight considering ONLY new patterns.
If nothing materially changed, say so.
"""
    else:
        safe_txn = make_json_safe(transactions[:15])
        prompt = f"""
{SYSTEM_PROMPT}

TRANSACTION_SAMPLE (PATTERN ONLY):
{json.dumps(safe_txn, indent=2)}

Answer:
1. Any unusual timing or clustering?
2. Any high-level behavioral patterns?

Do NOT invent numbers.
"""

    # -------------------------------
    # LLM Call
    # -------------------------------
    try:
        content = call_llm(
            prompt,
            temperature=0.25
        )

        payload = {
            "fingerprint": fingerprint,
            "transaction_count": len(transactions),
            "model": LLM_MODEL,
            "content": content,
        }

        _save_cache(payload)

        return {
            "type": "llm_transaction_patterns",
            "model": LLM_MODEL,
            "content": content,
            "cached": False,
        }

    except Exception:
        return {
            "type": "llm_transaction_patterns",
            "model": None,
            "content": (
                "Transaction pattern analysis unavailable.\n"
                "Underlying transaction data remains valid."
            ),
            "cached": False,
        }
