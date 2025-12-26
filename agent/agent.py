from datetime import date

import agent.state_builder as state_builder
from agent.forecast import forecast_month_end_balance
from agent.policy import decide
from agent.executor import execute

from agent.goal_engine import (
    FinancialGoal,
    evaluate_goal,
    goal_based_action
)

from agent.user_profile import UserProfile


def run_agent(df, metrics=None, user: UserProfile | None = None):
    """
    Unified Agent Loop:
    observe → predict → reason → act → align with goals
    """

    # ================================
    # 1️⃣ OBSERVE (State Construction)
    # ================================
    if user is not None:
        state = state_builder.build_financial_state(df, user)
    else:
        # Backward compatibility
        state = state_builder.build_financial_state(df)

    # Attach bank-truth (accounting layer)
    if metrics is not None:
        state["bank_reported_income"] = float(metrics["total_income"])
        state["bank_reported_expense"] = float(metrics["total_expense"])

    # ================================
    # 2️⃣ PREDICT (Short-term Forecast)
    # ================================
    forecast_balance = forecast_month_end_balance(df)

    # ================================
    # 3️⃣ POLICY DECISIONS (Reactive)
    # ================================
    actions = decide(state, forecast_balance)
    responses = execute(actions, state)

    # ================================
    # 4️⃣ GOAL-BASED REASONING (Deliberative)
    # ================================
    goal_evaluation = None

    if metrics is not None:
        goal = FinancialGoal(
            name="Save ₹20,000",
            target_amount=20000,
            deadline=date(2026, 3, 31),
            priority="high"
        )

        goal_eval = evaluate_goal(goal, metrics)
        goal_action = goal_based_action(goal_eval)

        goal_evaluation = goal_eval

        # Avoid duplicate actions
        if goal_action["action"] not in actions:
            actions.append(goal_action["action"])

        responses.append(goal_action["message"])

    # ================================
    # 5️⃣ FINAL AGENT OUTPUT
    # ================================
    return {
        "state": state,
        "forecast_balance": round(forecast_balance, 2),
        "actions": sorted(set(actions)),
        "responses": responses,
        "goal_evaluation": goal_evaluation
    }
