# analytics/merchant_normalizer.py

import re

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
