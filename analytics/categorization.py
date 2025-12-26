import pandas as pd
import re
from typing import Tuple, Optional

from agent.categories import CATEGORIES
from analytics.merchant_normalizer import normalize_merchant
from analytics.llm_categorizer import llm_categorize_merchant
from analytics.llm_name_classifier import llm_is_business
from analytics.merchant_memory import lookup_merchant_category

# save_merchant_category is OPTIONAL – don’t crash if missing
try:
    from analytics.merchant_memory import save_merchant_category
except ImportError:
    save_merchant_category = None


# ==================================================
# USER SELF IDENTIFIERS (CRITICAL)
# ==================================================

SELF_UPI_ALIASES = {
    "sohamathawale",
    "sohamathawale20",
    "soham athawale",
}


def is_self_transfer(merchant: str, upi_id: str) -> bool:
    text = f"{merchant or ''} {upi_id or ''}".lower()
    return any(alias in text for alias in SELF_UPI_ALIASES)


# ==================================================
# TEXT HELPERS
# ==================================================

def normalize_text(*parts) -> str:
    return " ".join(p or "" for p in parts).lower()


def contains_any(text: str, keywords: list[str]) -> bool:
    return any(k in text for k in keywords)


# ==================================================
# HARD FACT KEYWORDS
# ==================================================

MANDATE_KEYWORDS = [
    "nach",
    "sip",
    "mutual fund",
    "cams",
    "bandhan",
]

# Prevent TRENT → RENT false positives
RENT_REGEX = re.compile(r"\b(rent|lease)\b", re.I)


# ==================================================
# PAYMENT RAIL METADATA
# ==================================================

RAIL_REGEX = {
    "UPI": re.compile(r"\bupi\b", re.I),
    "NEFT": re.compile(r"\bneft\b", re.I),
    "IMPS": re.compile(r"\bimps\b", re.I),
    "RTGS": re.compile(r"\brtgs\b", re.I),
}


def detect_payment_rail(description: str) -> str:
    text = (description or "").lower()
    for rail, rx in RAIL_REGEX.items():
        if rx.search(text):
            return rail
    return "OTHER"


# ==================================================
# LLM FALLBACK UPGRADE
# ==================================================

def upgrade_fallback_category(
    amount: float,
    llm_category: str,
    llm_confidence: float,
) -> Optional[str]:
    """
    Promote medium-confidence large spends
    """
    if abs(amount) >= 1000 and llm_confidence >= 0.60:
        if llm_category in {"Shopping", "Food", "Medical"}:
            return llm_category
    return None


# ==================================================
# CORE CATEGORIZATION LOGIC
# ==================================================

def categorize_transaction(
    description: str,
    merchant: str,
    upi_id: str,
    amount: float,
) -> Tuple[str, float, str]:

    text = normalize_text(description, merchant)

    # 1️⃣ INCOME
    if amount > 0:
        return "Income", 1.0, "rule"

    # 2️⃣ SELF TRANSFER
    if is_self_transfer(merchant, upi_id):
        return "Self Transfer", 1.0, "rule"

    # 3️⃣ MERCHANT MEMORY (AUTHORITATIVE)
    override = lookup_merchant_category(merchant)
    if override:
        return override, 1.0, "memory"

    # 4️⃣ INVESTMENTS / MANDATES
    if contains_any(text, MANDATE_KEYWORDS):
        return "Investments/Mandates", 0.95, "rule"

    # 5️⃣ RENT (SAFE WORD BOUNDARY)
    if RENT_REGEX.search(text):
        return "Rent", 0.95, "rule"

    # 6️⃣ LLM PRIMARY
    llm_category, llm_confidence = llm_categorize_merchant(merchant)

    if llm_confidence >= 0.80 and llm_category in CATEGORIES:
        # persist knowledge if available
        if save_merchant_category:
            try:
                save_merchant_category(
                    merchant=merchant,
                    category=llm_category,
                    confidence=llm_confidence,
                )
            except Exception:
                pass

        return llm_category, llm_confidence, "llm"

    # 6.5️⃣ UPGRADE LARGE MEDIUM-CONFIDENCE SPENDS
    upgraded = upgrade_fallback_category(
        amount, llm_category, llm_confidence
    )
    if upgraded:
        return upgraded, llm_confidence, "llm-upgrade"

    # 7️⃣ FINAL FALLBACK (CRITICAL SPLIT)
    if llm_is_business(merchant):
        return "Misc Businesses", 0.55, "fallback"

    return "Personal Transfers", 0.55, "fallback"


# ==================================================
# APPLY TO DATAFRAME
# ==================================================

def add_categories(df: pd.DataFrame) -> pd.DataFrame:
    if "description" not in df.columns or "amount" not in df.columns:
        raise ValueError("DataFrame must contain description & amount")

    df = df.copy()

    merchant_data = df["description"].apply(normalize_merchant)
    df["merchant"] = merchant_data.apply(
        lambda x: (x.get("merchant_name") or "").upper()
    )
    df["upi_id"] = merchant_data.apply(lambda x: x.get("upi_id"))

    df["payment_rail"] = df["description"].apply(detect_payment_rail)

    results = df.apply(
        lambda row: categorize_transaction(
            row["description"],
            row["merchant"],
            row["upi_id"],
            row["amount"],
        ),
        axis=1,
        result_type="expand",
    )

    df["category"] = results[0]
    df["category_confidence"] = results[1]
    df["category_source"] = results[2]

    # ✅ FIXED SAFETY CLAMP
    allowed = set(CATEGORIES) | {
        "Self Transfer",
        "Personal Transfers",
        "Misc Businesses",
    }

    df.loc[~df["category"].isin(allowed), "category"] = "Other"

    return df


# ==================================================
# SUMMARY HELPERS
# ==================================================

def category_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    TRUE discretionary expense view
    """
    expense_df = df[
        (df["amount"] < 0)
        & (~df["category"].isin([
            "Income",
            "Self Transfer",
            "Personal Transfers",
        ]))
    ].copy()

    expense_df["expense"] = expense_df["amount"].abs()

    return (
        expense_df
        .groupby("category", as_index=False)["expense"]
        .sum()
        .sort_values("expense", ascending=False)
        .reset_index(drop=True)
    )


def category_summary_all_debits(df: pd.DataFrame) -> pd.DataFrame:
    """
    Account truth: everything except income
    """
    debit_df = df[
        (df["amount"] < 0)
        & (df["category"] != "Income")
    ].copy()

    debit_df["amount_out"] = debit_df["amount"].abs()

    return (
        debit_df
        .groupby("category", as_index=False)["amount_out"]
        .sum()
        .sort_values("amount_out", ascending=False)
        .reset_index(drop=True)
    )
