import json
from agent.insights.utils import make_json_safe, call_llm

SYSTEM_PROMPT = """
You are a spending category analyst.

STRICT RULES:
- Use category totals ONLY
- Do NOT infer transactions
- Identify dominant categories and risk
"""

def generate_category_insights(category_summary):
    safe_summary = make_json_safe(category_summary)

    prompt = f"""
{SYSTEM_PROMPT}

CATEGORY_TOTALS:
{json.dumps(safe_summary, indent=2)}

Provide:
- Top spending categories
- Which are discretionary vs fixed
- One optimization suggestion
"""

    return call_llm(prompt, temperature=0.15)
