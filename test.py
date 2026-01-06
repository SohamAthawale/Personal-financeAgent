from sqlalchemy import text
from db import engine

try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("✅ Database connected:", result.scalar())
except Exception as e:
    print("❌ DB connection failed:", e)
