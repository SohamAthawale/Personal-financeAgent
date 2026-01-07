import pandas as pd

import pandas as pd


def forecast_month_end_balance(df: pd.DataFrame) -> float:
    """
    Forecast month-end balance using average daily net change.

    Defensive against:
    - empty dataframe
    - non-datetime dates
    - unsorted rows
    - missing balances
    - missing amount column
    - partial months
    """

    # --------------------------------------------------
    # 0️⃣ Empty / invalid dataframe
    # --------------------------------------------------
    if df is None or df.empty:
        return 0.0

    df = df.copy()

    # --------------------------------------------------
    # 1️⃣ Enforce datetime on date column
    # --------------------------------------------------
    if "date" not in df.columns:
        return 0.0

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    if df.empty:
        return 0.0

    # --------------------------------------------------
    # 2️⃣ Ensure amount column exists
    # --------------------------------------------------
    if "amount" not in df.columns:
        return 0.0

    # --------------------------------------------------
    # 3️⃣ Sort by date (CRITICAL)
    # --------------------------------------------------
    df = df.sort_values("date")

    # --------------------------------------------------
    # 4️⃣ Compute daily net cashflow
    # --------------------------------------------------
    daily_net = (
        df.groupby(df["date"].dt.date)["amount"]
        .sum()
    )

    if daily_net.empty:
        return 0.0

    avg_daily_change = float(daily_net.mean())

    # --------------------------------------------------
    # 5️⃣ Remaining days in month (safe)
    # --------------------------------------------------
    last_date = df["date"].iloc[-1]

    # Use calendar month length instead of fixed 30
    days_in_month = last_date.days_in_month
    days_left = max(0, days_in_month - last_date.day)

    projected_change = avg_daily_change * days_left

    # --------------------------------------------------
    # 6️⃣ Use last known balance if available
    # --------------------------------------------------
    if "balance" in df.columns:
        last_balance = df["balance"].iloc[-1]
        if pd.notna(last_balance):
            return round(float(last_balance + projected_change), 2)

    # --------------------------------------------------
    # 7️⃣ Fallback: return projected change only
    # --------------------------------------------------
    return round(float(projected_change), 2)
