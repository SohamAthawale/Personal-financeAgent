import json
from agent.insights.utils import make_json_safe, call_llm

SYSTEM_PROMPT = """
You are a financial reporting assistant.

STRICT RULES:
- Use ONLY the provided metrics
- Restate totals verbatim
- Do NOT mention transactions
- Do NOT compute or infer numbers
"""

def generate_financial_summary(metrics):
    safe_metrics = make_json_safe(metrics)

    prompt = f"""
{SYSTEM_PROMPT}

AUTHORITATIVE_METRICS:
{json.dumps(safe_metrics, indent=2)}

Provide:
1. Income, expense, net cashflow summary
2. Cashflow health (Low / Moderate / High)
"""

    return call_llm(prompt, temperature=0.05)
