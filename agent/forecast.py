def forecast_month_end_balance(df):
    daily = (
        df.groupby(df["date"].dt.date)["amount"]
        .sum()
    )

    avg_daily = daily.mean()

    days_left = 30 - df["date"].dt.day.iloc[-1]

    projected_change = avg_daily * days_left

    return round(df.iloc[-1]["balance"] + projected_change, 2)
