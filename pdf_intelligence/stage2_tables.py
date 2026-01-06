from collections import defaultdict
import re

# ----------------------------------
# Regexes
# ----------------------------------
NUMERIC_DATE = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")
TEXTUAL_DATE = re.compile(
    r"\b\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{4}\b",
    re.IGNORECASE
)

AMOUNT_REGEX = re.compile(r"\d{1,3}(?:,\d{3})*\.\d{2}")

Y_TOL = 8  # ⬅️ important: PDFs need wider tolerance


def detect_candidate_rows(words):
    """
    Robust transaction row detector for bank statements.
    Handles split words and multi-token dates.
    """

    by_page = defaultdict(list)
    for w in words:
        by_page[w["page"]].append(w)

    candidates = []

    for page_words in by_page.values():
        page_words.sort(key=lambda w: w["y"])

        current_row = []
        last_y = None

        for w in page_words:
            if last_y is None or abs(w["y"] - last_y) <= Y_TOL:
                current_row.append(w)
            else:
                if _is_transaction_row(current_row):
                    candidates.append(current_row)
                current_row = [w]

            last_y = w["y"]

        if current_row and _is_transaction_row(current_row):
            candidates.append(current_row)

    return candidates


def _is_transaction_row(row):
    texts = [w["text"] for w in row]
    joined = " ".join(texts)

    # Date must exist (numeric OR textual)
    has_date = (
        NUMERIC_DATE.search(joined)
        or TEXTUAL_DATE.search(joined)
    )

    # At least 2 numeric values (amount + balance)
    amount_count = sum(
        1 for t in texts if AMOUNT_REGEX.search(t)
    )

    return bool(has_date and amount_count >= 2)
