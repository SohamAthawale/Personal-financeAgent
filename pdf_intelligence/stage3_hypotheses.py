import re

AMOUNT_REGEX = re.compile(r"\d{1,3}(?:,\d{3})*\.\d{2}")


def extract_numeric_columns(rows, precision=5):
    """
    Extract numeric column x-positions with minimal rounding.
    """
    cols = set()

    for row in rows:
        for w in row:
            if AMOUNT_REGEX.search(w["text"]):
                cols.add(round(w["x0"], precision))

    return sorted(cols)


def generate_dual_hypotheses(cols):
    """
    Generate valid (withdrawal, deposit, balance) column schemas.
    Assumes balance is the rightmost column.
    """
    hyps = []

    for i, bal in enumerate(cols):
        left = cols[:i]

        for dep in left:
            for wit in left:
                if dep == wit:
                    continue

                # Ensure reasonable column spacing
                if abs(dep - wit) < 15:
                    continue

                hyps.append({
                    "type": "dual",
                    "deposit_x": dep,
                    "withdrawal_x": wit,
                    "balance_x": bal
                })

    return hyps


def generate_single_amount_hypotheses(cols):
    """
    Single signed-amount + balance fallback (legacy support).
    """
    hyps = []

    for i, bal in enumerate(cols):
        left = cols[:i]

        for amt in left:
            if abs(amt - bal) < 15:
                continue

            hyps.append({
                "type": "single",
                "amount_x": amt,
                "balance_x": bal
            })

    return hyps
