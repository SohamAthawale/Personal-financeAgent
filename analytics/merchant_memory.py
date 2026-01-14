# analytics/merchant_memory.py

import re
from typing import Optional

# ==================================================
# MERCHANT OVERRIDES (AUTHORITATIVE MEMORY)
# ==================================================
# Key = substring (lowercase)
# Value = final category
# NOTE: More specific keys MUST come before generic ones

MERCHANT_OVERRIDES = {
    # ------------------------------
    # Shopping / Retail
    # ------------------------------
    "trent limited": "Shopping",   # specific first
    "trent": "Shopping",
    "lifestyle": "Shopping",
    "life style": "Shopping",
    "westside": "Shopping",
    "pantaloons": "Shopping",
    "dmart": "Shopping",
    "zudio": "Shopping",
    "reliance trends": "Shopping",
    "shoppers stop": "Shopping",

    # ------------------------------
    # Food chains
    # ------------------------------
    "eversub": "Food",
    "subway": "Food",
    "mcdonald": "Food",
    "dominos": "Food",
    "kfc": "Food",
    "pizza": "Food",

    # ------------------------------
    # Telecom / Bills
    # ------------------------------
    "jio prepaid": "Bills",
    "airtel": "Bills",
    "vi prepaid": "Bills",
    "vodafone": "Bills",

    "chemist": "Medical",
    "CHEMIST": "Medical",
}

# ==================================================
# NORMALIZATION
# ==================================================

def normalize_merchant_key(text: str) -> str:
    """
    Normalize merchant text for substring matching.
    """
    if not text:
        return ""

    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# ==================================================
# LOOKUP (READ PATH)
# ==================================================

def lookup_merchant_category(merchant: str) -> Optional[str]:
    """
    Returns category if merchant matches authoritative memory.
    Otherwise returns None.
    """
    if not merchant:
        return None

    norm = normalize_merchant_key(merchant)

    for key, category in MERCHANT_OVERRIDES.items():
        if key in norm:
            return category

    return None


# ==================================================
# WRITE PATH (NO-OP, FUTURE SAFE)
# ==================================================

def save_merchant_category(
    merchant: str,
    category: str,
    confidence: Optional[float] = None,
) -> None:
    """
    Placeholder for future learning memory.

    Exists ONLY to satisfy imports and keep pipeline stable.
    Currently does nothing by design.
    """
    return None
