from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Date,
    DateTime,
    ForeignKey,
    Index,
    JSON,
)
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()


# =========================
# USER
# =========================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    phone = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    statements = relationship(
        "Statement",
        back_populates="user",
        cascade="all, delete-orphan"
    )


# =========================
# STATEMENT (1 per PDF)
# =========================
class Statement(Base):
    __tablename__ = "statements"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    original_filename = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="statements")
    transactions = relationship(
        "Transaction",
        back_populates="statement",
        cascade="all, delete-orphan"
    )


# =========================
# TRANSACTION
# =========================
class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)

    statement_id = Column(
        Integer,
        ForeignKey("statements.id"),
        nullable=False,
        index=True
    )

    date = Column(Date, nullable=False)
    description = Column(String, nullable=False)
    merchant = Column(String)

    amount = Column(Float, nullable=False)
    txn_type = Column(String)  # debit / credit

    category = Column(String)
    category_confidence = Column(Float)
    category_source = Column(String)

    raw = Column(JSON)  # full extracted row (future-proof)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    statement = relationship("Statement", back_populates="transactions")


# =========================
# INDEXES (performance)
# =========================
Index("ix_statement_user", Statement.user_id)
Index("ix_transaction_date", Transaction.date)
Index("ix_transaction_statement", Transaction.statement_id)
