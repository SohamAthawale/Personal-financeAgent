import pandas as pd
import re
from typing import Tuple, Optional

from agent.categories import CATEGORIES
from analytics.merchant_normalizer import normalize_merchant
from analytics.llm_categorizer import (
    llm_categorize_merchant,
    looks_like_person_name,
    is_micro_consumable,
)
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

RENT_REGEX = re.compile(r"\b(rent|lease)\b", re.I)

# 🚧 Structural non-person indicators
STRUCTURAL_HINTS = [
    "metro",
    "railway",
    "irct",
    "uts",
    "pos ",
    "paytm",
    "gpay",
    "phonepe",
]

# 🚧 Strong business indicators — never personal transfers
STRONG_BUSINESS_KEYWORDS = {
    "corporation",
    "corp",
    "india",
    "ltd",
    "limited",
    "pvt",
    "private",
    "priv",
    "company",
    "co ",
}
# ==================================================
# CORE CATEGORIZATION LOGIC
# ==================================================

def categorize_transaction(
    description: str,
    merchant: str,
    upi_id: str,
    amount: float,
    llm_cache: dict,
) -> Tuple[str, float, str]:

    text = normalize_text(description, merchant)
    merchant_l = merchant.lower()

    is_strong_business = any(k in merchant_l for k in STRONG_BUSINESS_KEYWORDS)

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

    # 5️⃣ RENT
    if RENT_REGEX.search(text):
        return "Rent", 0.95, "rule"

    # 6️⃣ LLM (CACHED)
    llm_category, llm_confidence = llm_cache.get(
        merchant, ("Other", 0.0)
    )

    # 🧃 MICRO-CONSUMABLE CORRECTION
    if is_micro_consumable(llm_category, amount):
        return "Food", 0.85, "micro-consumable"

    # ✅ STRONG LLM ACCEPTANCE
    if llm_confidence >= 0.80 and llm_category in CATEGORIES:

        # 🚫 Never treat structural merchants as people
        if (
            looks_like_person_name(merchant)
            and abs(amount) >= 500
            and not any(h in merchant_l for h in STRUCTURAL_HINTS)
        ):
            return "Personal Transfers", 0.75, "person-override"

        if save_merchant_category:
            try:
                save_merchant_category(
                    merchant=merchant,
                    category=llm_category,
                    confidence=llm_confidence,
                )
            except Exception:
                pass

        return llm_category, llm_confidence, "llm-strong"

    # 🟡 WEAK BUT USABLE LLM (LOCAL MERCHANTS)
    if (
        0.60 <= llm_confidence < 0.80
        and llm_category in {"Food", "Shopping", "Medical", "Transport", "Bills", "Subscriptions"}
        and llm_is_business(merchant)
    ):
        return llm_category, llm_confidence, "llm-weak"

    # 7️⃣ FINAL FALLBACK
    if llm_category in {"Food", "Medical", "Transport", "Bills", "Subscriptions", "Shopping"}:
        return llm_category, max(llm_confidence, 0.65), "llm-accepted"
    if is_strong_business:
        return "Misc Businesses", 0.65, "business-guard"
    
    return "Personal Transfers", 0.55, "fallback"


# ==================================================
# APPLY TO DATAFRAME (BATCHED LLM CALLS)
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

    unique_merchants = df["merchant"].unique()
    llm_cache = {
        m: llm_categorize_merchant(m)
        for m in unique_merchants if m
    }

    results = df.apply(
        lambda row: categorize_transaction(
            row["description"],
            row["merchant"],
            row["upi_id"],
            row["amount"],
            llm_cache,
        ),
        axis=1,
        result_type="expand",
    )

    df["category"] = results[0]
    df["category_confidence"] = results[1]
    df["category_source"] = results[2]

    allowed = set(CATEGORIES) | {
        "Income",
        "Self Transfer",
        "Personal Transfers",
        "Misc Businesses",
        "Investments/Mandates",
    }

    df.loc[~df["category"].isin(allowed), "category"] = "Other"

    return df


# ==================================================
# SUMMARY HELPERS
# ==================================================

def category_summary(df: pd.DataFrame) -> pd.DataFrame:
    expense_df = df[
        (df["amount"] < 0)
        & (~df["category"].isin([
            "Income",
            "Self Transfer",
            "Personal Transfers",
        ]))
    ].copy()

    if expense_df.empty:
        return pd.DataFrame(columns=["category", "expense"])

    expense_df["expense"] = expense_df["amount"].abs()

    return (
        expense_df
        .groupby("category", as_index=False)["expense"]
        .sum()
        .sort_values("expense", ascending=False)
        .reset_index(drop=True)
    )


def category_summary_all_debits(df: pd.DataFrame) -> pd.DataFrame:
    debit_df = df[
        (df["amount"] < 0)
        & (df["category"] != "Income")
    ].copy()

    if debit_df.empty:
        return pd.DataFrame(columns=["category", "amount_out"])

    debit_df["amount_out"] = debit_df["amount"].abs()

    return (
        debit_df
        .groupby("category", as_index=False)["amount_out"]
        .sum()
        .sort_values("amount_out", ascending=False)
        .reset_index(drop=True)
    )
