from datetime import date
from dateutil.relativedelta import relativedelta


# ==================================================
# DOMAIN OBJECT
# ==================================================
class FinancialGoal:
    def __init__(self, name, target_amount, deadline, priority="medium"):
        self.name = name
        self.target_amount = float(target_amount)
        self.deadline = deadline
        self.priority = priority


# ==================================================
# HELPERS
# ==================================================
def months_remaining(deadline: date) -> int:
    today = date.today()
    months = (deadline.year - today.year) * 12 + (deadline.month - today.month)
    return max(1, months)

def build_goal_projection(goal_eval):
    months = goal_eval["months_remaining"]
    current = goal_eval["current_monthly_saving"]
    required = goal_eval["required_monthly_saving"]

    actual = []
    ideal = []

    actual_total = 0
    ideal_total = 0

    for m in range(1, months + 1):
        actual_total += current
        ideal_total += required

        actual.append({
            "month": m,
            "amount": round(actual_total, 2),
        })

        ideal.append({
            "month": m,
            "amount": round(ideal_total, 2),
        })

    return {
        "actual": actual,
        "ideal": ideal,
    }

# ==================================================
# CORE GOAL EVALUATION (BACKWARD COMPATIBLE)
# ==================================================
def evaluate_goal(goal: FinancialGoal, metrics: dict) -> dict:
    """
    Evaluates feasibility + savings health + timeline projection.

    This function is:
    - Deterministic
    - Auditable
    - LLM-free
    """

    # -------------------------------
    # Timeline inputs
    # -------------------------------
    months_left = months_remaining(goal.deadline)

    total_income = float(metrics.get("total_income", 0))
    total_expense = float(metrics.get("total_expense", 0))

    monthly_cashflows = metrics.get("monthly_cashflow", [])
    observed_months = max(1, len(monthly_cashflows))

    avg_monthly_income = total_income / observed_months
    avg_monthly_expense = total_expense / observed_months
    avg_monthly_saving = avg_monthly_income - avg_monthly_expense

    required_monthly_saving = goal.target_amount / months_left

    feasible = avg_monthly_saving >= required_monthly_saving

    # -------------------------------
    # Projection logic (NEW)
    # -------------------------------
    projection = project_goal_timeline(
        goal=goal,
        avg_monthly_saving=avg_monthly_saving
    )

    return {
        # 🔒 Existing fields (UI-safe)
        "goal": goal.name,
        "months_remaining": int(months_left),
        "required_monthly_saving": round(required_monthly_saving, 2),
        "current_monthly_saving": round(avg_monthly_saving, 2),
        "feasible": bool(feasible),

        # 🆕 NEW analytics
        "projection": projection,
    }


# ==================================================
# GOAL PROJECTION ENGINE (NEW)
# ==================================================
def project_goal_timeline(
    *,
    goal: FinancialGoal,
    avg_monthly_saving: float,
) -> dict:
    """
    Determines when the goal will be achieved at current savings rate.
    """

    # ❌ No savings → impossible
    if avg_monthly_saving <= 0:
        return {
            "status": "impossible",
            "reason": "negative_or_zero_savings",
            "avg_monthly_saving": round(avg_monthly_saving, 2),
        }

    months_needed = goal.target_amount / avg_monthly_saving

    today = date.today()
    achieved_by = today + relativedelta(months=int(months_needed))

    deadline_gap_months = (
        (goal.deadline.year - achieved_by.year) * 12
        + (goal.deadline.month - achieved_by.month)
    )

    return {
        "status": "projected",
        "avg_monthly_saving": round(avg_monthly_saving, 2),
        "months_needed": int(months_needed),
        "achieved_by": achieved_by.isoformat(),
        "deadline": goal.deadline.isoformat(),
        "months_before_deadline": int(deadline_gap_months),
        "overshoots_deadline": deadline_gap_months < 0,
        "achieves_early": deadline_gap_months > 0,
    }


# ==================================================
# RULE-BASED ACTION ENGINE (UPGRADED)
# ==================================================
def goal_based_action(goal_eval: dict) -> dict:
    projection = goal_eval.get("projection", {})

    # ❌ Impossible goal
    if projection.get("status") == "impossible":
        return {
            "action": "CRITICAL",
            "message": (
                f"Goal '{goal_eval['goal']}' cannot be achieved with "
                f"negative or zero monthly savings."
            ),
        }

    # ⚠️ Misses deadline
    if projection.get("overshoots_deadline"):
        return {
            "action": "INCREASE_SAVINGS",
            "message": (
                f"At current savings, you will miss the deadline for "
                f"'{goal_eval['goal']}' by "
                f"{abs(projection['months_before_deadline'])} months."
            ),
        }

    # 🚀 Achieves early
    if projection.get("achieves_early") and projection.get("months_before_deadline", 0) >= 6:
        return {
            "action": "AHEAD_OF_PLAN",
            "message": (
                f"You will reach '{goal_eval['goal']}' approximately "
                f"{projection['months_before_deadline']} months before the deadline."
            ),
        }

    # ✅ On track
    return {
        "action": "ON_TRACK",
        "message": "You are on track to reach your goal 🎯",
    }
