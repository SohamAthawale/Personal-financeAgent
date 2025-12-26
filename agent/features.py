def text_features(df):
    return (
        df["description"]
        .str.lower()
        .str.replace(r"[^a-z ]", "", regex=True)
    )
