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
