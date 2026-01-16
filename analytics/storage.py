from typing import List, Dict
from sqlalchemy.orm import Session

from models import Transaction


def save_transactions_db(
    *,
    db: Session,
    statement_id: int,
    transactions: List[Dict]
) -> None:
    """
    Persist extracted transactions to DB.

    Guarantees:
    - Statement-scoped (no cross-user pollution)
    - Idempotent per statement
    - No CSV / filesystem dependency
    """

    if not transactions:
        raise ValueError("No transactions to save")

    db.bulk_save_objects(
        [
            Transaction(
                statement_id=statement_id,
                date=t["date"],
                description=t["description"],
                merchant=t.get("merchant"),
                amount=t["amount"],
                txn_type=t.get("type"),
                raw=t,
            )
            for t in transactions
        ]
    )

    db.commit()


# ==================================================
# 🔥 ADDITIONS BELOW (NO EXISTING CODE MODIFIED)
# ==================================================

# ---- NEW: transaction fingerprinting (future-safe) ----

def compute_transaction_fingerprint(txn: Dict) -> str:
    """
    Stable fingerprint for idempotency & deduplication.

    Can later be stored in DB with a UNIQUE constraint.
    """
    parts = [
        str(txn.get("date")),
        str(txn.get("amount")),
        str(txn.get("description", "")).lower().strip(),
    ]
    return "|".join(parts)


# ---- NEW: safe bulk insert wrapper ----

def save_transactions_db_safe(
    *,
    db: Session,
    statement_id: int,
    transactions: List[Dict],
) -> int:
    """
    Safer wrapper with rollback protection.

    Returns:
    - number of transactions attempted
    """

    if not transactions:
        return 0

    try:
        save_transactions_db(
            db=db,
            statement_id=statement_id,
            transactions=transactions,
        )
        return len(transactions)

    except Exception:
        db.rollback()
        raise


# ---- NEW: pre-insert deduplication hook (optional) ----

def deduplicate_transactions(
    transactions: List[Dict],
) -> List[Dict]:
    """
    Removes exact duplicates in-memory before DB insert.
    Safe no-op for clean data.
    """
    seen = set()
    unique = []

    for txn in transactions:
        fp = compute_transaction_fingerprint(txn)
        if fp in seen:
            continue
        seen.add(fp)
        unique.append(txn)

    return unique


# ---- NEW: audit helper ----

def summarize_transactions(transactions: List[Dict]) -> Dict:
    """
    Lightweight audit summary for logging / monitoring.
    """
    if not transactions:
        return {
            "count": 0,
            "total_amount": 0.0,
        }

    return {
        "count": len(transactions),
        "total_amount": round(
            sum(float(t.get("amount", 0)) for t in transactions), 2
        ),
    }
