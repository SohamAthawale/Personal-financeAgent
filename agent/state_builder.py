import pandas as pd
import numpy as np
from agent.user_profile import UserProfile

REQUIRED_COLS = {"date", "deposit", "withdrawal", "balance"}

print(">>> USING FIXED build_financial_state <<<")


def build_financial_state(
    df: pd.DataFrame,
    user: UserProfile | None = None,
    period_days: int = 90
):
    """
    Build agent financial state.

    Guarantees:
    - Bank data is the only source of truth
    - Robust to sparse months
    - User profile is OPTIONAL
    """

    # -------------------------------
    # Validation
    # -------------------------------
    if df.empty:
        raise ValueError("Transaction dataframe is empty")

    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # -------------------------------
    # Enforce datetime
    # -------------------------------
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    if df.empty:
        raise ValueError("No valid dated transactions")

    # -------------------------------
    # Recent window
    # -------------------------------
    recent = df.sort_values("date").tail(period_days)

    # -------------------------------
    # Monthly aggregation
    # -------------------------------
    monthly = (
        recent
        .assign(month=lambda x: x["date"].dt.to_period("M"))
        .groupby("month", observed=True)[["deposit", "withdrawal"]]
        .sum()
        .sort_index()
    )

    if monthly.empty:
        raise ValueError("No monthly data available")

    # -------------------------------
    # ✅ ROLLING BEHAVIORAL AVERAGES (FIX)
    # -------------------------------
    avg_income = float(
        monthly["deposit"]
        .replace(0, np.nan)     # ignore zero-income months
        .mean()
        or 0.0
    )

    avg_expense = float(monthly["withdrawal"].mean())

    # -------------------------------
    # Savings rate
    # -------------------------------
    savings_rate = (
        (avg_income - avg_expense) / avg_income
        if avg_income > 0 else 0.0
    )

    # -------------------------------
    # Liquidity
    # -------------------------------
    current_balance = float(recent.iloc[-1]["balance"])
    daily_expense = avg_expense / 30 if avg_expense > 0 else 0.0

    liquidity_days = (
        current_balance / daily_expense
        if daily_expense > 0 else float("inf")
    )

    # -------------------------------
    # Optional user context
    # -------------------------------
    fixed_expenses = user.fixed_expenses if user else None
    declared_income = user.monthly_income if user else None

    discretionary_spend = (
        max(avg_expense - fixed_expenses, 0.0)
        if fixed_expenses is not None
        else None
    )

    # -------------------------------
    # Stability metrics
    # -------------------------------
    expense_std = (
        float(monthly["withdrawal"].std())
        if len(monthly) > 1 else 0.0
    )

    income_std = (
        float(monthly["deposit"].std())
        if len(monthly) > 1 else 0.0
    )

    # -------------------------------
    # Final state
    # -------------------------------
    return {
        # Behavioral (rolling)
        "avg_monthly_income": round(avg_income, 2),
        "avg_monthly_expense": round(avg_expense, 2),
        "savings_rate": round(savings_rate, 3),
        "liquidity_days": round(liquidity_days, 1),
        "current_balance": round(current_balance, 2),

        # Volatility
        "expense_std": round(expense_std, 2),
        "income_std": round(income_std, 2),

        # Optional user context

    }
