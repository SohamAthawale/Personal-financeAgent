import json
from agent.insights.utils import make_json_safe, call_llm

SYSTEM_PROMPT = """
You are a transaction pattern analyst.

STRICT RULES:
- Transactions are qualitative only
- Do NOT compute totals
- Do NOT invent amounts
- Use words like: frequent, clustered, large, repeated
"""

def generate_transaction_patterns(transactions):
    safe_txn = make_json_safe(transactions[:15])

    prompt = f"""
{SYSTEM_PROMPT}

TRANSACTION_SAMPLE (PATTERN ONLY):
{json.dumps(safe_txn, indent=2)}

Answer:
- Any unusual timing or clustering?
- Any high-level behavioral patterns?
"""

    return call_llm(prompt, temperature=0.25)
