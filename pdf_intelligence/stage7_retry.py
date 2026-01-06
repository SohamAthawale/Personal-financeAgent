def retry_with_variants(
    rows,
    choose_best_hypothesis,
    accept_threshold=0.95,
    retry_threshold=0.7,
):
    """
    Try safe structural variants and return:
    - accepted schema
    - OR multiple candidates for LLM arbitration
    """

    variants = []

    # 1️⃣ Original
    variants.append(("original", rows))

    # 2️⃣ Reverse order
    variants.append(("reversed", list(reversed(rows))))

    # 3️⃣ Drop first 3 rows (skip headers / opening balance)
    if len(rows) > 6:
        variants.append(("drop_first_3", rows[3:]))

    # 4️⃣ Drop last 3 rows (skip footers)
    if len(rows) > 6:
        variants.append(("drop_last_3", rows[:-3]))

    candidates = []

    for name, variant_rows in variants:
        schema, confidence = choose_best_hypothesis(variant_rows)

        if schema is None:
            continue

        candidates.append({
            "schema": schema,
            "confidence": confidence,
            "variant": name
        })

        # 🔒 Deterministic early accept
        if confidence >= accept_threshold:
            return {
                "decision": "accepted",
                "schema": schema,
                "confidence": confidence,
                "variant": name
            }

    # -------------------------------------------------
    # Decide next step
    # -------------------------------------------------
    if len(candidates) >= 1:
        return {
            "decision": "needs_arbitration",
            "candidates": candidates
        }

    if candidates and candidates[0]["confidence"] >= retry_threshold:
        return {
            "decision": "accepted",
            **candidates[0]
        }

    return {
        "decision": "rejected"
    }
