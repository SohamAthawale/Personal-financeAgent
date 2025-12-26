def decide(state, forecast_balance):
    actions = []

    savings_rate = state.get("savings_rate", 0)
    liquidity_days = state.get("liquidity_days", float("inf"))
    job_type = state.get("job_type", "unknown")
    income_stability = state.get("income_stability", "medium")
    discretionary = state.get("discretionary_spend", 0)
    fixed_expenses = state.get("fixed_expenses", 0)

    # ----------------------------------
    # 1. Balance risk (highest priority)
    # ----------------------------------
    if forecast_balance < 0:
        actions.append("WARN_NEGATIVE_BALANCE")

    elif forecast_balance < fixed_expenses:
        actions.append("LOW_BALANCE_WARNING")

    # ----------------------------------
    # 2. Liquidity risk
    # ----------------------------------
    if liquidity_days < 3:
        actions.append("EMERGENCY_LIQUIDITY_ALERT")
    elif liquidity_days < 7:
        actions.append("CRITICAL_ALERT")
    elif liquidity_days < 14:
        actions.append("LOW_LIQUIDITY_WARNING")

    # ----------------------------------
    # 3. Savings behavior
    # ----------------------------------
    if savings_rate < 0:
        actions.append("OVERSPENDING_ALERT")

    elif savings_rate < 0.05:
        actions.append("URGENT_SAVINGS_PLAN")

    elif savings_rate < 0.10:
        actions.append("SUGGEST_SAVINGS_PLAN")

    # ----------------------------------
    # 4. Job-context adjustments
    # ----------------------------------
    if job_type in {"student", "intern"}:
        # Relax expectations for early-career profiles
        if savings_rate < 0.05 and discretionary > 0:
            actions.append("STUDENT_SPEND_OPTIMIZATION")

    elif income_stability == "low":
        actions.append("BUILD_EMERGENCY_FUND")

    # ----------------------------------
    # 5. Discretionary spending check
    # ----------------------------------
    if discretionary > fixed_expenses * 0.5:
        actions.append("REDUCE_DISCRETIONARY_SPEND")

    return sorted(set(actions))
