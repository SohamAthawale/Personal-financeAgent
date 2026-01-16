# analytics/merchant_normalizer.py

import re

# =====================================================
# EXISTING CODE (UNCHANGED)
# =====================================================

# Common noise tokens in bank narrations
NOISE_TOKENS = [
    "upi", "neft", "imps", "rtgs",
    "sent", "received", "to", "from",
    "txn", "ref", "no", "id",
    "payment", "pay", "using"
]

VPA_REGEX = re.compile(
    r"([a-z0-9.\-_]{3,})@([a-z]{2,})",
    re.IGNORECASE
)
UPI_PATH_RX = re.compile(r"upi/([^/]+)/(\d{6,})", re.IGNORECASE)

def normalize_text(text: str) -> str:
    if not text:
        return "unknown"

    t = text.lower()

    # remove numbers
    t = re.sub(r"\d+", " ", t)

    # remove noise tokens
    for token in NOISE_TOKENS:
        t = t.replace(token, " ")

    # collapse spaces
    t = re.sub(r"\s+", " ", t).strip()

    return t or "unknown"


def extract_upi_id(description: str) -> str | None:
    if not description:
        return None

    m = VPA_REGEX.search(description.lower())
    if m:
        return f"{m.group(1)}@{m.group(2)}"

    return None

def normalize_merchant(description: str) -> dict:
    if not description:
        return {"merchant_name": "UNKNOWN", "upi_id": None}

    desc = description.lower()

    # 1️⃣ UPI path-based extraction
    m = UPI_PATH_RX.search(desc)
    if m:
        merchant = m.group(1).strip().upper()
        upi_id = f"{merchant}_{m.group(2)}"
        return {
            "merchant_name": merchant,
            "upi_id": upi_id
        }

    # 2️⃣ Fallback VPA
    upi_id = extract_upi_id(desc)

    return {
        "merchant_name": normalize_text(desc).upper(),
        "upi_id": upi_id
    }

# =====================================================
# 🔥 ADDITIONS BELOW — ZERO BREAKING CHANGES
# =====================================================

# ---- NEW: location / branch noise handling ----
LOCATION_SUFFIXES = {
    "blr", "bengaluru", "bangalore",
    "mum", "mumbai",
    "del", "delhi",
    "hyd", "hyderabad",
    "chn", "chennai",
    "kol", "kolkata",
    "pune"
}

def canonicalize_merchant_name(name: str) -> str:
    """
    Generates a stable merchant key for:
    - merchant_memory
    - rule engine
    - analytics
    Does NOT replace merchant_name.
    """
    if not name or name == "UNKNOWN":
        return "unknown"

    n = name.lower()

    # normalize separators
    n = re.sub(r"[._\-]", " ", n)

    parts = []
    for p in n.split():
        if p in LOCATION_SUFFIXES:
            continue
        if len(p) <= 2:
            continue
        parts.append(p)

    return parts[0] if parts else "unknown"


def enrich_normalized_merchant(result: dict) -> dict:
    """
    ADD-ON ENRICHMENT FUNCTION
    Call this AFTER normalize_merchant()

    Adds:
    - merchant_key (canonical, memory-safe)
    - raw_merchant (debug/audit)
    """

    merchant_name = result.get("merchant_name", "UNKNOWN")
    upi_id = result.get("upi_id")

    base = merchant_name
    if upi_id and "@" in upi_id:
        base = upi_id.split("@")[0]

    result["merchant_key"] = canonicalize_merchant_name(base)
    result["raw_merchant"] = merchant_name

    return result
