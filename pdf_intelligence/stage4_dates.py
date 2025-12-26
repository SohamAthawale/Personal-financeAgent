import re
import pandas as pd

DATE_REGEX = re.compile(r"\d{2}[/-]\d{2}[/-]\d{2,4}")

def extract_date(row):
    for w in row:
        if DATE_REGEX.search(w["text"]):
            return pd.to_datetime(DATE_REGEX.search(w["text"]).group(), dayfirst=True)
    return None
