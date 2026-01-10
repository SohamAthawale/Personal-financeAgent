from datetime import date

from agent.insights.utils import make_json_safe
import agent.state_builder as state_builder
from agent.forecast import forecast_month_end_balance
from agent.policy import decide
from agent.executor import execute

from agent.goal_engine import (
    FinancialGoal,
    evaluate_goal,
    goal_based_action
)


def run_agent(df, metrics=None, goals=None):
    """
    Unified Agent Loop

    Guarantees:
    - BANK data is the source of truth
    - User goals affect advice ONLY
    """

    # ================================
    # 1️⃣ OBSERVE (BANK DATA)
    # ================================
    state = state_builder.build_financial_state(
        df=df,
        user=None
    )

    if metrics:
        state["bank_reported_income"] = float(metrics["total_income"])
        state["bank_reported_expense"] = float(metrics["total_expense"])

    # ================================
    # 2️⃣ PREDICT
    # ================================
    forecast_balance = forecast_month_end_balance(df)

    # ================================
    # 3️⃣ POLICY (REACTIVE)
    # ================================
    actions = decide(state, forecast_balance)
    responses = execute(actions, state)

    # ================================
    # 🆕 STRUCTURED RECOMMENDATIONS
    # ================================
    recommendations = {
        "critical": [],
        "forecast": [],
        "goals": []
    }

    # --- Map actions → critical / forecast buckets ---
    for action in actions:
        if action in ("reduce_spending", "emergency_mode", "pause_goals"):
            recommendations["critical"].append({
                "action": action,
                "message": f"Immediate action required: {action.replace('_', ' ')}.",
                "severity": "critical",
                "confidence": 0.95
            })
        else:
            recommendations["forecast"].append({
                "action": action,
                "message": f"Recommended action: {action.replace('_', ' ')}.",
                "severity": "medium",
                "confidence": 0.85
            })

    # ================================
    # 4️⃣ GOAL REASONING (USER-DEFINED)
    # ================================
    goal_evaluations = []

    if metrics and goals:
        for goal in goals:
            eval_result = evaluate_goal(goal, metrics)
            goal_action = goal_based_action(eval_result)

            goal_evaluations.append(eval_result)

            if goal_action["action"] not in actions:
                actions.append(goal_action["action"])

            responses.append(goal_action["message"])

            # 🆕 Structured goal recommendation
            recommendations["goals"].append({
                "goal": getattr(goal, "name", "unknown"),
                "message": goal_action["message"],
                "action": goal_action["action"],
                "severity": eval_result.get("severity", "info"),
                "confidence": eval_result.get("confidence", 0.8)
            })

    # ================================
    # 5️⃣ FINAL OUTPUT
    # ================================
    result = {
        "state": state,
        "forecast_balance": round(float(forecast_balance), 2),

        # 🔒 Keep existing fields
        "actions": sorted(set(actions)),
        "responses": list(dict.fromkeys(responses)),
        "goal_evaluations": goal_evaluations,

        # 🆕 New structured output
        "recommendations": recommendations,
    }

    return make_json_safe(result)
