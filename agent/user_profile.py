from dataclasses import dataclass
from typing import Optional


@dataclass
class UserProfile:
    monthly_income: float
    job_type: str              # "student", "intern", "salaried", "freelancer"
    income_stability: str      # "low", "medium", "high"
    fixed_expenses: float = 0  # rent, EMI, etc
    age: Optional[int] = None
