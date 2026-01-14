from agent.insights.utils import call_llm

try:
    from config.llm import LLM_ENABLED
except ImportError:
    LLM_ENABLED = True


def generate_goal_insights(goal_evaluations, force_refresh=False):
    """
    LLM explanation layer for goal evaluations.
    No math, no projections — explanation only.
    """

    if not LLM_ENABLED or not goal_evaluations:
        return []

    prompt = f"""
You are a financial advisor.

Below are evaluated financial goals with computed metrics.

Explain clearly:
- Why each goal is feasible or not
- What trade-offs the user can consider
- What practical actions they can take
- Do NOT repeat numbers verbatim
- Do NOT invent new numbers

Goal evaluations:
{goal_evaluations}
"""

    response = call_llm(
        prompt=prompt,
        temperature=0.3,
    )

    if not response:
        return []

    return [
        {
            "message": response,
            "severity": "medium",
        }
    ]
