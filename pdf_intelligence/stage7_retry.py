def retry_with_variants(rows, choose_best_hypothesis,
                        accept_threshold=0.95,
                        retry_threshold=0.7):
    """
    Try safe structural variants of the same rows and
    return the best hypothesis + confidence.
    """

    variants = []

    # 1️⃣ Original
    variants.append(("original", rows))

    # 2️⃣ Reverse order
    variants.append(("reversed", list(reversed(rows))))

    # 3️⃣ Drop first 3 rows
    if len(rows) > 6:
        variants.append(("drop_first_3", rows[3:]))

    # 4️⃣ Drop last 3 rows
    if len(rows) > 6:
        variants.append(("drop_last_3", rows[:-3]))

    best_schema = None
    best_score = 0.0
    best_variant = None

    for name, variant_rows in variants:
        schema, score = choose_best_hypothesis(variant_rows)

        if score > best_score:
            best_schema = schema
            best_score = score
            best_variant = name

        # Early accept
        if score >= accept_threshold:
            break

    # Decide outcome
    if best_score >= accept_threshold:
        decision = "accepted"
    elif best_score >= retry_threshold:
        decision = "needs_arbitration"
    else:
        decision = "rejected"

    return {
        "schema": best_schema,
        "confidence": best_score,
        "variant": best_variant,
        "decision": decision
    }
