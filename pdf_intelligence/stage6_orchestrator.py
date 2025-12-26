from pdf_intelligence.stage3_hypotheses import (
    extract_numeric_columns,
    generate_dual_hypotheses,
    generate_single_amount_hypotheses
)
from pdf_intelligence.stage4_validation import validate_hypothesis
from pdf_intelligence.stage4_dates import extract_date
from pdf_intelligence.stage5_confidence import score_hypothesis


def choose_best_hypothesis(rows, min_rows=10):
    """
    Selects the best schema hypothesis.
    - Uses ranking_score for comparison
    - Returns calibrated confidence ∈ [0, 1]
    """

    # -------------------------------
    # Filter rows with valid dates
    # -------------------------------
    dated = [(extract_date(r), r) for r in rows if extract_date(r) is not None]
    if len(dated) < min_rows:
        return None, 0.0

    dated.sort(key=lambda x: x[0])
    sorted_rows = [r for _, r in dated]

    # -------------------------------
    # Generate hypotheses
    # -------------------------------
    cols = extract_numeric_columns(sorted_rows)

    dual_hyps = generate_dual_hypotheses(cols)
    single_hyps = generate_single_amount_hypotheses(cols)

    evaluated = []

    # -------------------------------
    # Validate + score hypotheses
    # -------------------------------
    for h in dual_hyps + single_hyps:
        res = validate_hypothesis(sorted_rows, h)

        total = res["reconciled"] + res["errors"]
        if total < min_rows:
            continue

        # Base confidence (0..1)
        base_confidence = score_hypothesis(res)

        # Ranking score (can exceed 1)
        ranking_score = base_confidence

        # ✅ Prefer dual schema ONLY for ranking
        if h["type"] == "dual":
            ranking_score *= 1.3

        evaluated.append({
            "schema": h,
            "ranking_score": ranking_score,
            "confidence": base_confidence
        })

    if not evaluated:
        return None, 0.0

    # -------------------------------
    # Select best hypothesis
    # -------------------------------
    best = max(evaluated, key=lambda x: x["ranking_score"])

    final_schema = best["schema"]

    # ✅ HARD CLAMP confidence
    final_confidence = min(1.0, max(0.0, best["confidence"]))

    return final_schema, final_confidence
