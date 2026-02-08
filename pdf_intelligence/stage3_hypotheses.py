import re

AMOUNT_REGEX = re.compile(
    r"\b(?:\d+\.\d{2}|\d{1,3}(?:,\d{3})*\.\d{2}|\d{1,3}(?:,\d{2})+,\d{3}\.\d{2})\b"
)


def _should_use_right_edge(x0_vals, x1_vals) -> bool:
    """
    Detect right-aligned numeric columns by comparing positional stability.
    If right edges are significantly more stable than left edges, use x1.
    """
    if not x0_vals or not x1_vals:
        return False

    u0 = len(set(round(v, 1) for v in x0_vals))
    u1 = len(set(round(v, 1) for v in x1_vals))

    if u1 == 0:
        return False

    # Prefer x1 only when it is notably more stable
    return u1 <= max(2, int(u0 * 0.6))


def extract_numeric_columns(rows, precision=5):
    """
    Extract numeric column x-positions with minimal rounding.
    """
    cols = set()
    x0_vals = []
    x1_vals = []

    for row in rows:
        for w in row:
            if AMOUNT_REGEX.search(w["text"]):
                x0_vals.append(w["x0"])
                x1_vals.append(w["x1"])

    use_right_edge = _should_use_right_edge(x0_vals, x1_vals)

    for row in rows:
        for w in row:
            if AMOUNT_REGEX.search(w["text"]):
                anchor = w["x1"] if use_right_edge else w["x0"]
                cols.add(round(anchor, precision))

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
