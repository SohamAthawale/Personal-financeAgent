from collections import defaultdict
import re

DATE_REGEX = re.compile(r"\d{2}[/-]\d{2}[/-]\d{2,4}")
AMOUNT_REGEX = re.compile(r"\d{1,3}(?:,\d{3})*\.\d{2}")

Y_TOL = 6  # vertical tolerance in PDF units


def detect_candidate_rows(words):
    """
    Robust transaction row detection for bank statements.
    Correctly merges multi-line rows (critical for opening deposits).
    """

    # Group by page first
    by_page = defaultdict(list)
    for w in words:
        by_page[w["page"]].append(w)

    candidates = []

    for page, page_words in by_page.items():
        # Sort top to bottom
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

        # Flush last row
        if current_row and _is_transaction_row(current_row):
            candidates.append(current_row)

    return candidates


def _is_transaction_row(row):
    has_date = any(DATE_REGEX.search(w["text"]) for w in row)
    has_amount = any(AMOUNT_REGEX.search(w["text"]) for w in row)
    return has_date and has_amount
