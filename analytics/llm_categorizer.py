import json
import requests
import re
from functools import lru_cache

# ==================================================
# BACKEND CONFIG (NO HARDCODED VALUES)
# ==================================================
try:
    from config.llm import LLM_ENABLED, OLLAMA_URL, LLM_MODEL
except ImportError:
    # Safe defaults if config not present
    LLM_ENABLED = True
    OLLAMA_URL = "http://localhost:11434/api/generate"
    LLM_MODEL = "llama3"


# ==================================================
# ALLOWED OUTPUT SPACE (STRICT)
# ==================================================
ALLOWED_CATEGORIES = [
    "Food",
    "Transport",
    "Shopping",
    "Bills",
    "Subscriptions",
    "Medical",
    "Rent",
    "Transfer",
    "Other"
]


# ==================================================
# SYSTEM PROMPT (CONFIDENCE-CALIBRATED)
# ==================================================
SYSTEM_PROMPT = """
You are a financial transaction categorizer.

Your task:
- Categorize the merchant name into EXACTLY ONE category.
- Use merchant name semantics (brand, business type).
- Be conservative in ambiguous cases.
- If the merchant appears to be a PERSON or a personal UPI payment,
  prefer the category "Transfer" with LOW confidence.
- DO NOT guess aggressively for unknown merchants.

Confidence rules (VERY IMPORTANT):
- 0.90–1.00 → Very confident, well-known brand or obvious category
- 0.75–0.89 → Reasonably confident, common merchant
- 0.60–0.74 → Weak signal, some ambiguity
- <0.60     → Highly uncertain

Guidelines:
- Restaurants, cafes, dairies → Food
- Metro, railways, transport authorities → Transport
- Telecom recharges, utilities → Bills
- Online services, apps, memberships → Subscriptions
- Retail brands, clothing, footwear → Shopping
- Pharmacies, chemists → Medical

Output ONLY valid JSON.
"""


# ==================================================
# CONFIDENCE RESCALING (MODEL CALIBRATION)
# ==================================================
def rescale_confidence(confidence: float) -> float:
    """
    🔧 UPDATED:
    - Reduced inflation
    - Prevents weak guesses becoming 90%+
    """
    if confidence <= 0.5:
        return confidence

    # Old: 0.7 + (confidence - 0.5) * 0.6
    # New: softer scaling
    return min(1.0, 0.65 + (confidence - 0.5) * 0.5)


# ==================================================
# PERSON-NAME HEURISTIC (SAFETY SIGNAL)
# ==================================================

# 🔧 UPDATED: supports ALL-CAPS bank statements
PERSON_NAME_RX = re.compile(
    r"^[A-Z ]{3,}$",
    re.I
)

def looks_like_person_name(name: str) -> bool:
    """
    Conservative heuristic.
    Used ONLY as a safety signal by callers.
    """
    if not name:
        return False

    name = name.strip()

    # 🔥 NEW: explicit ALL-CAPS + short token guard
    if name.isupper() and 1 <= len(name.split()) <= 3:
        return True

    return bool(PERSON_NAME_RX.match(name))


# ==================================================
# MICRO-CONSUMABLE SIGNAL
# ==================================================
def is_micro_consumable(category: str, amount: float) -> bool:
    """
    Signals likely food/consumables misclassified as Shopping.
    Decision remains with caller.
    """
    return (
        category == "Shopping"
        and abs(amount) <= 150
    )


# ==================================================
# LLM CATEGORIZATION (BACKEND ONLY)
# ==================================================
@lru_cache(maxsize=1024)
def llm_categorize_merchant(merchant: str) -> tuple[str, float]:
    """
    Backend-only semantic categorization.
    Returns: (category, confidence)
    """

    # -------------------------------
    # Hard guards
    # -------------------------------
    if not merchant:
        return "Other", 0.0

    if not LLM_ENABLED:
        return "Other", 0.0

    # -------------------------------
    # Prompt
    # -------------------------------
    prompt = f"""
{SYSTEM_PROMPT}

Allowed categories:
{ALLOWED_CATEGORIES}

Merchant:
"{merchant}"

Output:
{{ "category": "...", "confidence": 0.0 }}
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
                    "temperature": 0.0,
                    "top_p": 1.0
                }
            },
            timeout=20
        )

        resp.raise_for_status()

        raw = resp.json().get("response", "")

        # -------------------------------
        # Strict JSON extraction
        # -------------------------------
        start, end = raw.find("{"), raw.rfind("}") + 1
        if start == -1 or end == -1:
            return "Other", 0.0

        data = json.loads(raw[start:end])

        category = data.get("category", "Other")
        confidence = float(data.get("confidence", 0.0))

        # -------------------------------
        # Output validation
        # -------------------------------
        if category not in ALLOWED_CATEGORIES:
            return "Other", 0.0

        confidence = max(0.0, min(confidence, 1.0))
        confidence = rescale_confidence(confidence)

        # 🔥 NEW: cap confidence for unknown / uppercase merchants
        if merchant.isupper() and category in ("Food", "Shopping"):
            confidence = min(confidence, 0.75)

        return category, confidence

    except Exception:
        return "Other", 0.0


# ==================================================
# 🔥 ADDITIONS BELOW (NO EXISTING CODE MODIFIED)
# ==================================================

# ---- Deterministic pre-rules to avoid LLM ----

RULE_BASED_HINTS = {
    "zomato": "Food",
    "swiggy": "Food",
    "dominos": "Food",
    "pizza": "Food",
    "uber": "Transport",
    "ola": "Transport",
    "rapido": "Transport",
    "amazon": "Shopping",
    "flipkart": "Shopping",
    "myntra": "Shopping",
    "netflix": "Subscriptions",
    "spotify": "Subscriptions",
    "hotstar": "Subscriptions",
}

def rule_based_category_hint(
    merchant_key: str | None
) -> tuple[str | None, float]:
    """
    Fast deterministic category hint.
    """
    if not merchant_key:
        return None, 0.0

    key = merchant_key.lower()

    for rule, category in RULE_BASED_HINTS.items():
        if rule in key:
            return category, 0.9

    return None, 0.0


# ---- Safe wrapper with short-circuiting ----

def smart_categorize_merchant(
    merchant_name: str,
    merchant_key: str | None = None,
) -> tuple[str, float, str]:
    """
    Unified categorization entrypoint.
    """

    # 1️⃣ Rule-based short-circuit
    rule_cat, rule_conf = rule_based_category_hint(merchant_key)
    if rule_cat:
        return rule_cat, rule_conf, "rule"

    # 2️⃣ LLM fallback
    cat, conf = llm_categorize_merchant(merchant_name)
    return cat, conf, "llm"


# ---- Confidence gate for memory writes ----

def llm_confidence_safe(confidence: float) -> bool:
    """
    Prevent low-confidence LLM outputs from being persisted.
    """
    return confidence >= 0.8
