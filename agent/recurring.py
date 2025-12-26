def detect_recurring(df):
    recurring = []

    grouped = df.groupby("description")

    for desc, g in grouped:
        if len(g) < 3:
            continue

        intervals = g["date"].diff().dt.days.dropna()

        if intervals.between(25, 35).mean() > 0.6:
            recurring.append(desc)

    return recurring
