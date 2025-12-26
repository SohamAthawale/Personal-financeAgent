import pandas as pd
import numpy as np
from agent.user_profile import UserProfile


REQUIRED_COLS = {"date", "deposit", "withdrawal", "balance"}
print(">>> USING UPDATED build_financial_state <<<")

def build_financial_state(

    df: pd.DataFrame,
    user: UserProfile,
    period_days: int = 90
):
    # -------------------------------
    # Validation
    # -------------------------------
    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns for agent state: {missing}")

    if df.empty:
        raise ValueError("Transaction dataframe is empty")

    # Ensure datetime
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    # -------------------------------
    # Recent window
    # -------------------------------
    recent = df.sort_values("date").tail(period_days)

    if recent.empty:
        raise ValueError("No valid recent transactions found")

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

    # 🔴 IMPORTANT FIX: use latest month, not mean
    last_month = monthly.iloc[-1]

    avg_income = float(last_month["deposit"])
    avg_expense = float(last_month["withdrawal"])

    # -------------------------------
    # Savings rate
    # -------------------------------
    savings_rate = (
        (avg_income - avg_expense) / avg_income
        if avg_income > 0 else 0.0
    )

    # -------------------------------
    # Liquidity (days you can survive)
    # -------------------------------
    daily_expense = avg_expense / 30 if avg_expense > 0 else 0.0

    liquidity_days = (
        recent.iloc[-1]["balance"] / daily_expense
        if daily_expense > 0 else float("inf")
    )

    # -------------------------------
    # Discretionary spending
    # -------------------------------
    discretionary_spend = max(
        avg_expense - user.fixed_expenses,
        0.0
    )

    # -------------------------------
    # Final state (agent memory)
    # -------------------------------
    return {
        # Transaction-derived
        "avg_monthly_income": round(avg_income, 2),
        "avg_monthly_expense": round(avg_expense, 2),
        "savings_rate": round(savings_rate, 3),
        "liquidity_days": round(liquidity_days, 1),
        "current_balance": round(float(recent.iloc[-1]["balance"]), 2),

        # Stability metrics
        "expense_std": round(
            float(monthly["withdrawal"].std()) if len(monthly) > 1 else 0.0,
            2
        ),
        "income_std": round(
            float(monthly["deposit"].std()) if len(monthly) > 1 else 0.0,
            2
        ),

        # User context
        "declared_income": round(user.monthly_income, 2),
        "job_type": user.job_type,
        "income_stability": user.income_stability,
        "fixed_expenses": round(user.fixed_expenses, 2),
        "discretionary_spend": round(discretionary_spend, 2),
    }
