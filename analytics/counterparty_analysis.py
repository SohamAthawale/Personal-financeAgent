# analytics/counterparty_analysis.py

import pandas as pd
import re

# =========================
# EXISTING CODE (UNCHANGED)
# =========================

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

# =====================================================
# 🔥 ADDITIONS BELOW (NO EXISTING CODE MODIFIED)
# =====================================================

# ---- Heuristics for personal vs merchant UPI ----

BANK_HANDLES = {
    "oksbi", "okhdfc", "okicici", "okaxis",
    "paytm", "ibl", "upi", "ybl"
}

PHONE_RX = re.compile(r"^\d{9,12}@")

def detect_counterparty_type(upi_id: str | None) -> str:
    """
    Lightweight deterministic classification.
    Returns: person | merchant | unknown
    """
    if not upi_id:
        return "unknown"

    u = upi_id.lower()

    if PHONE_RX.match(u):
        return "person"

    if "@" in u:
        handle = u.split("@")[1]
        if handle in BANK_HANDLES:
            # still ambiguous → name-based heuristic
            name = u.split("@")[0]
            if name.isdigit():
                return "person"
            if len(name) <= 6:
                return "merchant"

    return "unknown"


def enrich_counterparty_summary(
    df: pd.DataFrame,
    top_n: int = 10
) -> pd.DataFrame:
    """
    Adds counterparty type signals on top of existing summary.
    Does NOT replace upi_counterparty_summary().
    """

    summary = upi_counterparty_summary(df, top_n=top_n)

    if summary.empty:
        return summary

    summary["counterparty_type"] = summary["upi_id"].apply(
        detect_counterparty_type
    )

    return summary


def upi_counterparty_by_type(
    df: pd.DataFrame,
    counterparty_type: str,
    top_n: int = 10
) -> pd.DataFrame:
    """
    Filtered view for:
    - person (Transfers)
    - merchant (Spending)
    """

    enriched = enrich_counterparty_summary(df, top_n=top_n * 3)

    return (
        enriched[enriched["counterparty_type"] == counterparty_type]
        .head(top_n)
        .reset_index(drop=True)
    )
