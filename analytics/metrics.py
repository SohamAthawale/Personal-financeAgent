import pandas as pd


# ==================================================
# HELPERS
# ==================================================
def is_opening_balance_row(row):
    """
    Detect true opening balance rows so they can be excluded
    from transaction-based analytics.
    """
    desc = str(row.get("description", "")).lower()

    return (
        row.get("deposit", 0) > 0
        and row.get("withdrawal", 0) == 0
        and row.get("balance", -1) == row.get("deposit", -2)
        and any(k in desc for k in ["opening balance", "brought forward"])
    )


# ==================================================
# CORE METRICS (DATAFRAME-BASED)
# ==================================================
def compute_metrics_from_df(df: pd.DataFrame):
    """
    Compute financial metrics from a transactions DataFrame.

    Expected columns:
    - date
    - description
    - deposit
    - withdrawal
    - balance
    - confidence
    """

    if df.empty:
        raise ValueError("No transactions to compute metrics")

    # ---------- Schema validation ----------
    required = {
        "date",
        "description",
        "deposit",
        "withdrawal",
        "balance",
        "confidence",
    }

    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # ---------- Normalize ----------
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])

    # ---------- Remove ONLY true opening balance ----------
    df_txn = df.loc[~df.apply(is_opening_balance_row, axis=1)].copy()

    # ---------- Core totals ----------
    total_income = round(df_txn["deposit"].sum(), 2)
    total_expense = round(df_txn["withdrawal"].sum(), 2)
    net_cashflow = round(total_income - total_expense, 2)

    # ---------- Safety invariant ----------
    assert round(total_income - total_expense, 2) == net_cashflow, (
        "Cashflow invariant violated"
    )

    # ---------- Monthly cashflow ----------
    df_txn["month"] = df_txn["date"].dt.to_period("M")

    monthly_cashflow = (
        df_txn
        .groupby("month", as_index=False)[["deposit", "withdrawal"]]
        .sum()
        .assign(amount=lambda x: x["deposit"] - x["withdrawal"])
        .astype({"month": str})
        [["month", "amount"]]
        .to_dict(orient="records")
    )

    # ---------- Metrics payload ----------
    metrics = {
        "total_income": total_income,
        "total_expense": total_expense,
        "net_cashflow": net_cashflow,
        "monthly_cashflow": monthly_cashflow,
        "avg_confidence": round(df_txn["confidence"].mean(), 3),
    }

    return metrics, df_txn
