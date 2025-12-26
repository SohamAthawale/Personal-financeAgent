import pandas as pd
from pathlib import Path

DATA_DIR = Path("/Users/sohamathawale/Documents/GitHub/Personal-financeAgent/output")
DATA_DIR.mkdir(exist_ok=True)

CSV_PATH = DATA_DIR / "transactions_clean.csv"

# ✅ AUTHORITATIVE SCHEMA
COLUMNS = [
    "date",
    "description",
    "deposit",
    "withdrawal",
    "amount",
    "balance",
    "confidence",
    "source_pdf"
]


def save_transactions_csv(transactions):
    """
    Persist transactions in an idempotent, bank-safe way.

    Rules:
    - Overwrite on each run (no duplication)
    - Preserve semantic columns (deposit / withdrawal / amount)
    - Backward compatible with older CSVs
    """

    df = pd.DataFrame(transactions)

    if df.empty:
        raise ValueError("No transactions to save")

    # -------------------------------
    # Ensure required columns exist
    # -------------------------------
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = 0.0 if col in ("deposit", "withdrawal", "amount") else None

    # Enforce schema + order
    df = df[COLUMNS]

    # -------------------------------
    # Optional: defensive deduplication
    # (safe even if unnecessary)
    # -------------------------------
    df = df.drop_duplicates(
        subset=["date", "description", "amount", "balance", "source_pdf"]
    )

    # -------------------------------
    # 🔒 OVERWRITE (IDEMPOTENT)
    # -------------------------------
    df.to_csv(CSV_PATH, index=False)

    return df
