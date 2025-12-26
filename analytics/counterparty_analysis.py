# analytics/counterparty_analysis.
import pandas as pd


def upi_counterparty_summary(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """
    Returns top UPI counterparties by:
    - total amount
    - transaction count
    """

    if "upi_id" not in df.columns:
        raise ValueError("upi_id column missing")

    upi_df = df[df["upi_id"].notna()].copy()

    if upi_df.empty:
        return pd.DataFrame(columns=[
            "upi_id", "transaction_count", "total_amount"
        ])

    upi_df["abs_amount"] = upi_df["amount"].abs()

    summary = (
        upi_df
        .groupby("upi_id")
        .agg(
            transaction_count=("upi_id", "count"),
            total_amount=("abs_amount", "sum")
        )
        .reset_index()
        .sort_values(
            by=["total_amount", "transaction_count"],
            ascending=False
        )
        .head(top_n)
    )

    return summary
