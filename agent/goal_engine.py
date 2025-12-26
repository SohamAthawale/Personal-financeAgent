from datetime import date


class FinancialGoal:
    def __init__(self, name, target_amount, deadline, priority="medium"):
        self.name = name
        self.target_amount = target_amount
        self.deadline = deadline
        self.priority = priority


def months_remaining(deadline):
    today = date.today()
    return max(
        1,
        (deadline.year - today.year) * 12 + deadline.month - today.month
    )


def evaluate_goal(goal, metrics):
    months_left = months_remaining(goal.deadline)

    # ---------- derive monthly values safely ----------
    monthly_cashflows = metrics.get("monthly_cashflow", [])
    num_months = max(1, len(monthly_cashflows))

    avg_monthly_income = metrics["total_income"] / num_months
    avg_monthly_expense = metrics["total_expense"] / num_months
    avg_monthly_saving = avg_monthly_income - avg_monthly_expense

    required_monthly_saving = goal.target_amount / months_left

    return {
        "goal": goal.name,
        "months_remaining": months_left,
        "required_monthly_saving": round(required_monthly_saving, 2),
        "current_monthly_saving": round(avg_monthly_saving, 2),
        "feasible": avg_monthly_saving >= required_monthly_saving,
    }


def goal_based_action(goal_eval):
    if not goal_eval["feasible"]:
        return {
            "action": "REDUCE_EXPENSES",
            "message": (
                f"You need to save ₹{goal_eval['required_monthly_saving']} per month. "
                f"Currently saving ₹{goal_eval['current_monthly_saving']}."
            ),
        }

    return {
        "action": "ON_TRACK",
        "message": "You are on track to reach your goal 🎯",
    }
