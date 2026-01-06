# pdf_intelligence/stage4_dates.py

import re
import pandas as pd

# Numeric: 01/12/2025 or 01-12-25
NUMERIC_DATE = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")

# Textual: 01 Dec 2025, 1 January 2026
TEXTUAL_DATE = re.compile(
    r"\b\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{4}\b",
    re.IGNORECASE
)

def extract_date(row):
    texts = [w.get("text", "") for w in row]
    joined = " ".join(texts)

    # Numeric date
    m = NUMERIC_DATE.search(joined)
    if m:
        try:
            return pd.to_datetime(m.group(), dayfirst=True)
        except Exception:
            pass

    # Textual date
    m = TEXTUAL_DATE.search(joined)
    if m:
        try:
            return pd.to_datetime(m.group())
        except Exception:
            pass

    return None

