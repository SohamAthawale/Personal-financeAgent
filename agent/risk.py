def assess_risk(state):
    if state["liquidity_days"] < 7:
        return "HIGH"

    if state["liquidity_days"] < 14:
        return "MEDIUM"

    return "LOW"
