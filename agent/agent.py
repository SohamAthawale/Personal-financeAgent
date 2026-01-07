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

from datetime import date

import agent.state_builder as state_builder
from agent.forecast import forecast_month_end_balance
from agent.policy import decide
from agent.executor import execute

from agent.goal_engine import (
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

    # ================================
    # 5️⃣ FINAL OUTPUT
    # ================================
    result = {
            "state": state,
            "forecast_balance": round(float(forecast_balance), 2),
            "actions": sorted(set(actions)),
            "responses": responses,
            "goal_evaluations": goal_evaluations,
        }

        # ✅ CRITICAL FIX
    return make_json_safe(result)