import re

AMOUNT_REGEX = re.compile(r"\d{1,3}(?:,\d{3})*\.\d{2}")


def extract_amount(row, target_x, tol=15):
    if target_x is None:
        return None

    for w in row:
        if abs(w["x0"] - target_x) <= tol:
            m = AMOUNT_REGEX.search(w["text"])
            if m:
                return float(m.group().replace(",", ""))

    return None


def validate_hypothesis(rows, h):
    reconciled = 0
    errors = 0
    prev_balance = None

    for row in rows:
        bal = extract_amount(row, h.get("balance_x"))

        # ---------------------------------
        # Skip rows without balance
        # ---------------------------------
        if bal is None:
            continue

        # ---------------------------------
        # OPENING BALANCE ROW
        # ---------------------------------
        if prev_balance is None:
            prev_balance = bal
            reconciled += 1
            continue

        # ---------------------------------
        # SINGLE COLUMN SCHEMA
        # ---------------------------------
        if h["type"] == "single":
            amt = extract_amount(row, h.get("amount_x"))

            if amt is None:
                prev_balance = bal
                continue

            if (
                abs(prev_balance + amt - bal) <= 1
                or abs(prev_balance - amt - bal) <= 1
            ):
                reconciled += 1
            else:
                errors += 1

        # ---------------------------------
        # DUAL COLUMN SCHEMA
        # ---------------------------------
        elif h["type"] == "dual":
            dep = extract_amount(row, h.get("deposit_x"))
            wd  = extract_amount(row, h.get("withdrawal_x"))

            if dep is not None:
                if abs(prev_balance + dep - bal) <= 1:
                    reconciled += 1
                else:
                    errors += 1

            elif wd is not None:
                if abs(prev_balance - wd - bal) <= 1:
                    reconciled += 1
                else:
                    errors += 1

            else:
                # Balance-only row (interest postings, adjustments)
                reconciled += 1

        prev_balance = bal

    return {
        "reconciled": reconciled,
        "errors": errors,
    }
