from datetime import date


class FinancialGoal:
    def __init__(self, name, target_amount, deadline, priority="medium"):
        self.name = name
        self.target_amount = float(target_amount)
        self.deadline = deadline
        self.priority = priority


def months_remaining(deadline):
    today = date.today()
    months = (deadline.year - today.year) * 12 + (deadline.month - today.month)
    return max(1, months)


def evaluate_goal(goal, metrics):
    months_left = months_remaining(goal.deadline)

    total_income = float(metrics.get("total_income", 0))
    total_expense = float(metrics.get("total_expense", 0))

    monthly_cashflows = metrics.get("monthly_cashflow", [])
    num_months = max(1, len(monthly_cashflows))

    avg_monthly_income = total_income / num_months
    avg_monthly_expense = total_expense / num_months
    avg_monthly_saving = avg_monthly_income - avg_monthly_expense

    required_monthly_saving = goal.target_amount / months_left

    return {
        "goal": goal.name,
        "months_remaining": int(months_left),
        "required_monthly_saving": round(required_monthly_saving, 2),
        "current_monthly_saving": round(avg_monthly_saving, 2),
        "feasible": bool(avg_monthly_saving >= required_monthly_saving),
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
