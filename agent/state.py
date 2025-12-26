from dataclasses import dataclass
from typing import Dict, List


@dataclass
class FinancialState:
    period_days: int

    # Core aggregates
    avg_monthly_income: float
    avg_monthly_expense: float
    savings_rate: float

    # Volatility & risk
    expense_std: float
    income_std: float
    liquidity_days: float

    # Behavioral
    top_categories: Dict[str, float]
    recurring_merchants: List[str]

    # Trends
    expense_trend: float
    income_trend: float

    # Snapshot
    current_balance: float
