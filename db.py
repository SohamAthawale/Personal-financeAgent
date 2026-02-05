import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://finance_user@localhost:5432/finance_agent",
)
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine)
)
