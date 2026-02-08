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

AMOUNT_REGEX = re.compile(
    r"\b(?:\d+\.\d{2}|\d{1,3}(?:,\d{3})*\.\d{2}|\d{1,3}(?:,\d{2})+,\d{3}\.\d{2})\b"
)

Y_TOL = 8  # ⬅️ important: PDFs need wider tolerance

# Merge nearby line-groups when dates and amounts split across lines
MERGE_GAP = Y_TOL * 2
MAX_MERGE_LINES = 3


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

        # 1) Base line-grouping (existing behavior)
        line_groups = []
        current_row = []
        last_y = None

        for w in page_words:
            if last_y is None or abs(w["y"] - last_y) <= Y_TOL:
                current_row.append(w)
            else:
                if current_row:
                    line_groups.append(current_row)
                current_row = [w]

            last_y = w["y"]

        if current_row:
            line_groups.append(current_row)

        for group in line_groups:
            if _is_transaction_row(group):
                candidates.append(group)

        # 2) Date-anchored merge fallback (additive only)
        for i, group in enumerate(line_groups):
            if not _has_date(group):
                continue
            if _is_transaction_row(group):
                continue

            merged = list(group)
            merged_lines = 1
            last_group_y = _group_y(group)

            for j in range(i + 1, len(line_groups)):
                if merged_lines >= MAX_MERGE_LINES:
                    break

                next_group = line_groups[j]

                if _has_date(next_group):
                    break

                gap = _group_y(next_group) - last_group_y
                if gap > MERGE_GAP:
                    break

                merged.extend(next_group)
                merged_lines += 1
                last_group_y = _group_y(next_group)

                if _is_transaction_row(merged):
                    candidates.append(merged)
                    break

    return candidates


def _group_y(row):
    if not row:
        return 0
    return sum(w["y"] for w in row) / len(row)


def _has_date(row):
    texts = [w["text"] for w in row]
    joined = " ".join(texts)
    return bool(
        NUMERIC_DATE.search(joined)
        or TEXTUAL_DATE.search(joined)
    )


def _count_amounts(row):
    texts = [w["text"] for w in row]
    return sum(1 for t in texts if AMOUNT_REGEX.search(t))


def _is_transaction_row(row):
    has_date = _has_date(row)
    amount_count = _count_amounts(row)
    return bool(has_date and amount_count >= 2)
