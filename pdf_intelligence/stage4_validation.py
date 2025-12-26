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
        bal = extract_amount(row, h["balance_x"])
        if bal is None:
            continue

        # ✅ BOOTSTRAP FIRST ROW
        if prev_balance is None:
            reconciled += 1
            prev_balance = bal
            continue

        # ---------------- SINGLE COLUMN ----------------
        if h["type"] == "single":
            amt = extract_amount(row, h["amount_x"])
            if amt is None:
                continue

            if abs(prev_balance + amt - bal) <= 1 or abs(prev_balance - amt - bal) <= 1:
                reconciled += 1
            else:
                errors += 1

        # ---------------- DUAL COLUMN ----------------
        elif h["type"] == "dual":
            dep = extract_amount(row, h["deposit_x"])
            wd = extract_amount(row, h["withdrawal_x"])

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

        prev_balance = bal

    return {
        "reconciled": reconciled,
        "errors": errors
    }
