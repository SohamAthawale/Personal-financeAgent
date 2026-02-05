from pathlib import Path

# ==================================================
# PDF INTELLIGENCE PIPELINE
# ==================================================
from pdf_intelligence.stage1_layout import extract_layout
from pdf_intelligence.stage2_tables import detect_candidate_rows
from pdf_intelligence.stage6_orchestrator import choose_best_hypothesis
from pdf_intelligence.stage7_retry import retry_with_variants
from pdf_intelligence.stage8_llm_arbitration import llm_arbitrate
from pdf_intelligence.stage9_extraction import extract_transactions

# ==================================================
# ANALYTICS
# ==================================================
from analytics.storage import save_transactions_csv
from analytics.metrics import compute_metrics_from_csv
from analytics.categorization import (
    add_categories,
    category_summary,
    category_summary_all_debits
)
from analytics.counterparty_analysis import upi_counterparty_summary

# ==================================================
# AGENT + INSIGHTS
# ==================================================
from agent.agent import run_agent
from agent.user_profile import UserProfile

from agent.insights.financial_summary import generate_financial_summary
from agent.insights.transaction_patterns import generate_transaction_patterns
from agent.insights.category_insights import generate_category_insights


# ==================================================
# CONFIG
# ==================================================
PDF_PATH = r"/Users/sohamathawale/Downloads/Account_November 2025_XX6735.pdf"

CSV_PATH = Path(
    "/Users/sohamathawale/Documents/GitHub/Personal-financeAgent/output/transactions_clean.csv"
)


# ==================================================
# USER CONTEXT
# ==================================================
user_profile = UserProfile(
    monthly_income=25000,
    job_type="student",
    income_stability="low",
    fixed_expenses=12000
)


# ==================================================
# STAGES 1–2: LAYOUT + CANDIDATE ROWS
# ==================================================
words = extract_layout(PDF_PATH)
rows = detect_candidate_rows(words)


# ==================================================
# STAGE 6: SCHEMA DETECTION
# ==================================================
schema, confidence = choose_best_hypothesis(rows)

if confidence >= 0.9:
    final = {
        "schema": schema,
        "confidence": confidence,
        "decision": "accepted"
    }
else:
    final = retry_with_variants(rows, choose_best_hypothesis)
    if final["decision"] == "needs_arbitration":
        arb = llm_arbitrate(final.get("candidates", []))
        if arb:
            final = arb

print("\nFINAL RESULT:")
print(final)


# ==================================================
# STAGE 9: TRANSACTION EXTRACTION
# ==================================================
if not final.get("schema"):
    raise RuntimeError("❌ Transactions not extracted")

transactions = extract_transactions(
    rows=rows,
    schema=final["schema"],
    confidence=final["confidence"],
    source_pdf=PDF_PATH
)

print(f"\n✅ Extracted {len(transactions)} transactions")


# ==================================================
# STAGE 10: STORAGE (IDEMPOTENT)
# ==================================================
save_transactions_csv(transactions)


# ==================================================
# STAGE 10.5: METRICS (BANK-AUTHORITATIVE)
# ==================================================
metrics, df_txn = compute_metrics_from_csv(csv_path=CSV_PATH)

print("\n📊 METRICS (Authoritative)")
print(metrics)


# ==================================================
# STAGE 10.6: LLM-FIRST CATEGORIZATION
# ==================================================
df_txn = add_categories(df_txn)


# ==================================================
# VIEW 1: EXPENSE-ONLY CATEGORY SPENDING
# ==================================================
category_spending = category_summary(df_txn)

print("\n📂 CATEGORY-WISE SPENDING (Expenses Only)")
print(category_spending)


# ==================================================
# VIEW 2: ALL DEBITS (ACCOUNT-LEVEL TRUTH)
# ==================================================
all_debits = category_summary_all_debits(df_txn)

print("\n📤 CATEGORY-WISE DEBITS (Including Transfers)")
print(all_debits)


# ==================================================
# DEBUG VIEW: LOW-CONFIDENCE / FALLBACK TRANSACTIONS
# ==================================================
debug_df = df_txn[
    (df_txn["category_source"] == "fallback") |
    (df_txn["category_confidence"] < 0.7)
].copy()

if not debug_df.empty:
    print("\n🧪 LOW-CONFIDENCE / FALLBACK TRANSACTIONS")
    print(
        debug_df[
            [
                "date",
                "description",
                "merchant",
                "amount",
                "category",
                "category_confidence",
                "category_source"
            ]
        ].sort_values("amount")
    )


# ==================================================
# STAGE 10.7: UPI COUNTERPARTY INTELLIGENCE
# ==================================================
upi_summary = upi_counterparty_summary(df_txn)

print("\n🔁 TOP UPI COUNTERPARTIES")
print(upi_summary)

metrics["top_upi_counterparties"] = (
    upi_summary.to_dict(orient="records")
)


# ==================================================
# STAGE 11: LLM INSIGHTS (SAFE INPUTS ONLY)
# ==================================================
financial_summary = generate_financial_summary(metrics)

transaction_patterns = generate_transaction_patterns(
    df_txn[["date", "description"]].to_dict(orient="records")
)

category_insights = generate_category_insights(
    category_spending.to_dict(orient="records")
)

print("\n📊 FINANCIAL SUMMARY (LLM)")
print(financial_summary)

print("\n🔍 TRANSACTION PATTERNS (LLM)")
print(transaction_patterns)

print("\n📂 CATEGORY INSIGHTS (LLM)")
print(category_insights)


# ==================================================
# STAGE 12: AGENTIC AI
# ==================================================
agent_result = run_agent(
    df=df_txn,
    metrics=metrics,
    user=user_profile
)

print("\n🧠 AGENTIC AI OUTPUT")

print("\n📌 Financial State:")
for k, v in agent_result["state"].items():
    print(f"  {k}: {v}")

print(f"\n📈 Forecasted Month-End Balance: ₹{agent_result['forecast_balance']}")

print("\n⚡ Agent Actions:")
for a in agent_result["actions"]:
    print(f"  - {a}")

print("\n🗣️ Agent Responses:")
for r in agent_result["responses"]:
    print(f"  • {r}")
