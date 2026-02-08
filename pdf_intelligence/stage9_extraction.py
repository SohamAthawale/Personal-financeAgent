import re
from pdf_intelligence.stage4_dates import extract_date
from pdf_intelligence.stage4_validation import extract_amount

SUMMARY_KEYWORDS = [
    "opening balance", "closing balance", "total",
    "summary", "interest", "page", "statement"
]

CR_REGEX = re.compile(r"([\d,]+\.\d{2})\s*\(cr\)", re.IGNORECASE)
DR_REGEX = re.compile(r"([\d,]+\.\d{2})\s*\(dr\)", re.IGNORECASE)

BALANCE_NUMBER_REGEX = re.compile(
    r"\b(?:\d+\.\d{2}|\d{1,3}(?:,\d{3})*\.\d{2}|\d{1,3}(?:,\d{2})+,\d{3}\.\d{2})\b"
)


# --------------------------------------------------
# Row filters
# --------------------------------------------------
def is_summary_row(row):
    text = " ".join(w["text"].lower() for w in row)
    return any(k in text for k in SUMMARY_KEYWORDS)


# --------------------------------------------------
# Description extraction + sanitization
# --------------------------------------------------
def clean_description(text: str, balance: float | None):
    """
    Remove balance-like numbers and (Cr)/(Dr) artifacts from narration.
    """
    if not text:
        return ""

    cleaned = text

    # Remove explicit (Cr)/(Dr)
    cleaned = CR_REGEX.sub("", cleaned)
    cleaned = DR_REGEX.sub("", cleaned)

    # Remove raw balance number if present
    if balance is not None:
        bal_str = f"{balance:,.2f}"
        cleaned = cleaned.replace(bal_str, "")

    # Remove any leftover numeric-only tokens
    cleaned = BALANCE_NUMBER_REGEX.sub("", cleaned)

    return " ".join(cleaned.split()).strip()


def extract_description(row, exclude_x=None, tol=15):
    parts = []
    for w in row:
        if exclude_x is not None and abs(w["x0"] - exclude_x) <= tol:
            continue
        if any(c.isalpha() for c in w["text"]):
            parts.append(w["text"])
    return " ".join(parts).strip()


# --------------------------------------------------
# Explicit Cr / Dr extraction
# --------------------------------------------------
def extract_explicit_dr_cr(row, balance_x, tol=15):
    """
    Extract (Cr)/(Dr) ONLY from non-balance columns.
    """
    for w in row:
        if abs(w["x0"] - balance_x) <= tol:
            continue  # ignore balance column

        text = w["text"]

        cr = CR_REGEX.search(text)
        if cr:
            return float(cr.group(1).replace(",", "")), 0.0

        dr = DR_REGEX.search(text)
        if dr:
            return 0.0, float(dr.group(1).replace(",", ""))

    return None, None


# --------------------------------------------------
# Main extraction
# --------------------------------------------------
def extract_transactions(rows, schema, confidence, source_pdf):
    transactions = []
    prev_balance = None

    for row in rows:
        if is_summary_row(row):
            continue

        date = extract_date(row)
        if date is None:
            continue

        balance = extract_amount(row, schema.get("balance_x"))
        if balance is None:
            continue

        deposit = withdrawal = None

        # 1️⃣ Explicit Cr / Dr (highest priority)
        deposit, withdrawal = extract_explicit_dr_cr(
            row,
            balance_x=schema.get("balance_x")
        )

        # 2️⃣ Dual schema support
        if deposit is None and withdrawal is None and schema["type"] == "dual":
            dep = extract_amount(row, schema.get("deposit_x"))
            wd = extract_amount(row, schema.get("withdrawal_x"))

            if dep is not None:
                deposit, withdrawal = dep, 0.0
            elif wd is not None:
                deposit, withdrawal = 0.0, wd

        # 3️⃣ Balance delta fallback
        if deposit is None and withdrawal is None:
            if prev_balance is not None:
                delta = balance - prev_balance
                if delta >= 0:
                    deposit, withdrawal = delta, 0.0
                else:
                    deposit, withdrawal = 0.0, -delta
            else:
                deposit = withdrawal = 0.0

        prev_balance = balance

        raw_desc = extract_description(
            row,
            exclude_x=schema.get("amount_x")
        )

        description = clean_description(raw_desc, balance)

        transactions.append({
            "date": date.date().isoformat(),
            "description": description,
            "amount": round(deposit - withdrawal, 2),
            "deposit": round(deposit, 2),
            "withdrawal": round(withdrawal, 2),
            "balance": round(balance, 2),
            "confidence": round(confidence, 3),
            "source_pdf": source_pdf
        })

    return transactions
