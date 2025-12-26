def execute(actions, state):
    messages = []

    for action in actions:
        if action == "CRITICAL_ALERT":
            messages.append(
                f"⚠️ You have only {state['liquidity_days']} days of buffer left."
            )

        if action == "SUGGEST_SAVINGS_PLAN":
            messages.append(
                "📉 Your savings rate is low. Reducing food spend by 15% helps."
            )

    return messages
