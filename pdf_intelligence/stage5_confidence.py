def score_hypothesis(result):
    total = result["reconciled"] + result["errors"]
    return result["reconciled"] / total if total else 0.0
