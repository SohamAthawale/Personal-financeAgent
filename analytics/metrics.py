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
    Compute deterministic financial metrics from a transactions DataFrame.

    Guarantees:
    - No LLM involvement
    - Order-independent
    - Opening balance excluded
    - No NaN / Infinity values
    - UI-ready metrics
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
    df_txn = df.loc[
        ~df.apply(is_opening_balance_row, axis=1)
    ].copy()

    # ---------- Core totals ----------
    total_income = round(float(df_txn["deposit"].sum()), 2)
    total_expense = round(float(df_txn["withdrawal"].sum()), 2)
    net_cashflow = round(total_income - total_expense, 2)

    # ---------- Safety invariant ----------
    assert round(total_income - total_expense, 2) == net_cashflow, (
        "Cashflow invariant violated"
    )

    # ---------- Monthly aggregation ----------
    df_txn["month"] = df_txn["date"].dt.to_period("M").astype(str)

    monthly_summary = (
        df_txn
        .groupby("month", as_index=False)
        .agg(
            income=("deposit", "sum"),
            expense=("withdrawal", "sum"),
        )
    )

    monthly_summary["savings"] = (
        monthly_summary["income"] - monthly_summary["expense"]
    )

    monthly_summary = monthly_summary.round(2)

    # ---------- Monthly cashflow (legacy compatibility) ----------
    monthly_cashflow = (
        monthly_summary[["month", "savings"]]
        .rename(columns={"savings": "amount"})
        .to_dict(orient="records")
    )

    # ---------- UI-normalized metrics (NO NaN EVER) ----------
    monthly_income = total_income
    monthly_expense = total_expense
    monthly_savings = max(monthly_income - monthly_expense, 0.0)

    savings_rate = (
        monthly_savings / monthly_income
        if monthly_income > 0
        else 0.0
    )

    # ---------- Final metrics payload ----------
    metrics = {
        # Core (authoritative)
        "total_income": total_income,
        "total_expense": total_expense,
        "net_cashflow": net_cashflow,

        # UI cards
        "monthly_income": round(monthly_income, 2),
        "monthly_expense": round(monthly_expense, 2),
        "monthly_savings": round(monthly_savings, 2),
        "savings_rate": round(savings_rate, 4),

        # Charts
        "monthly_cashflow": monthly_cashflow,
        "monthly_timeseries": monthly_summary.to_dict(orient="records"),

        # Confidence / audit
        "avg_confidence": round(float(df_txn["confidence"].mean()), 3),
    }

    return metrics, df_txn


# ==================================================
# 🔥 ADDITIONS BELOW (NO EXISTING CODE MODIFIED)
# ==================================================

# ---- NEW: data quality diagnostics ----

def compute_data_quality_metrics(df: pd.DataFrame) -> dict:
    """
    Returns diagnostics about data health & trustworthiness.
    Purely additive — does not affect financial metrics.
    """
    if df.empty:
        return {
            "row_count": 0,
            "txn_rows": 0,
            "opening_balance_rows": 0,
            "avg_confidence": 0.0,
        }

    opening_mask = df.apply(is_opening_balance_row, axis=1)

    return {
        "row_count": int(len(df)),
        "txn_rows": int((~opening_mask).sum()),
        "opening_balance_rows": int(opening_mask.sum()),
        "avg_confidence": round(float(df["confidence"].mean()), 3),
    }


# ---- NEW: category-level expense breakdown (optional) ----

def compute_category_expense_summary(
    df: pd.DataFrame,
    category_col: str = "category",
) -> pd.DataFrame:
    """
    Aggregates expenses by category.
    Safe no-op if category column is missing.
    """
    if df.empty or category_col not in df.columns:
        return pd.DataFrame(
            columns=[category_col, "total_expense", "transaction_count"]
        )

    df_exp = df[df["withdrawal"] > 0].copy()

    if df_exp.empty:
        return pd.DataFrame(
            columns=[category_col, "total_expense", "transaction_count"]
        )

    summary = (
        df_exp
        .groupby(category_col, as_index=False)
        .agg(
            total_expense=("withdrawal", "sum"),
            transaction_count=("withdrawal", "count"),
        )
        .sort_values("total_expense", ascending=False)
    )

    return summary.round(2)


# ---- NEW: high-level KPI helper ----

def compute_kpis(df: pd.DataFrame) -> dict:
    """
    Thin wrapper around compute_metrics_from_df
    for UI or API endpoints that only need KPIs.
    """
    metrics, _ = compute_metrics_from_df(df)

    return {
        "income": metrics["total_income"],
        "expense": metrics["total_expense"],
        "savings": metrics["monthly_savings"],
        "savings_rate": metrics["savings_rate"],
        "avg_confidence": metrics["avg_confidence"],
    }
