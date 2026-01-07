from datetime import datetime
from agent.goal_engine import FinancialGoal


def parse_user_goals(raw_goals):
    """
    Safely parse user-defined goals.
    - Never crashes
    - Skips invalid goals
    """

    goals = []

    if not raw_goals:
        return goals

    for g in raw_goals:
        try:
            goals.append(
                FinancialGoal(
                    name=g["name"],
                    target_amount=float(g["target_amount"]),
                    deadline=datetime.strptime(
                        g["deadline"], "%Y-%m-%d"
                    ).date(),
                    priority=g.get("priority", "medium"),
                )
            )
        except Exception:
            # Ignore malformed goals
            continue

    return goals
