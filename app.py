from flask import Flask, request, jsonify
from pathlib import Path
import tempfile

from sqlalchemy import text
from sqlalchemy.orm import Session

from db import engine, SessionLocal
from models import User

from pipeline.core import (
    parse_statement,
    compute_analytics,
    generate_insights_view,
    run_agent_view
)

from agent.user_profile import UserProfile

app = Flask(__name__)

# ==================================================
# USER HELPERS
# ==================================================
def get_or_create_user(db: Session, phone: str) -> User:
    user = db.query(User).filter(User.phone == phone).first()
    if user:
        return user

    user = User(phone=phone)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ==================================================
# 1️⃣ USER CREATE / FETCH
# ==================================================
@app.route("/api/user", methods=["POST"])
def create_or_get_user():
    data = request.json or {}

    phone = data.get("phone")
    if not phone:
        return jsonify({"status": "error", "message": "phone is required"}), 400

    db = SessionLocal()
    try:
        user = get_or_create_user(db, phone)
        return jsonify(
            {
                "status": "success",
                "user": {
                    "id": user.id,
                    "phone": user.phone,
                },
            }
        )
    finally:
        db.close()


# ==================================================
# 2️⃣ UPLOAD & PARSE STATEMENT
# ==================================================
@app.route("/api/statement/parse", methods=["POST"])
def parse_statement_route():
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file uploaded"}), 400

    phone = request.form.get("phone")
    if not phone:
        return jsonify({"status": "error", "message": "phone is required"}), 400

    file = request.files["file"]

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        file.save(tmp.name)
        pdf_path = tmp.name

    db = SessionLocal()
    try:
        user = get_or_create_user(db, phone)

        result = parse_statement(
            db=db,
            pdf_path=pdf_path,
            user_id=user.id,
        )

        return jsonify(result)
    finally:
        db.close()


# ==================================================
# 3️⃣ ANALYTICS (DASHBOARD)
# ==================================================
@app.route("/api/statement/analytics", methods=["GET"])
def analytics_route():
    phone = request.args.get("phone")
    if not phone:
        return jsonify({"status": "error", "message": "phone is required"}), 400

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.phone == phone).first()
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404

        result = compute_analytics(
            db=db,
            user_id=user.id,
        )
        return jsonify(result)
    finally:
        db.close()


# ==================================================
# 4️⃣ INSIGHTS (LLM)
# ==================================================
@app.route("/api/statement/insights", methods=["GET"])
def insights_route():
    phone = request.args.get("phone")
    if not phone:
        return jsonify({"status": "error", "message": "phone is required"}), 400

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.phone == phone).first()
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404

        result = generate_insights_view(
            db=db,
            user_id=user.id,
        )
        return jsonify(result)
    finally:
        db.close()


# ==================================================
# 5️⃣ AGENT RECOMMENDATIONS
# ==================================================
@app.route("/api/agent/recommendations", methods=["POST"])
def agent_route():
    data = request.json or {}

    phone = data.get("phone")
    if not phone:
        return jsonify({"status": "error", "message": "phone is required"}), 400

    db = SessionLocal()
    try:
        user_db = db.query(User).filter(User.phone == phone).first()
        if not user_db:
            return jsonify({"status": "error", "message": "User not found"}), 404

        # Temporary static profile (can come from frontend later)
        user_profile = UserProfile(
            monthly_income=data.get("monthly_income", 25000),
            job_type=data.get("job_type", "student"),
            income_stability=data.get("income_stability", "low"),
            fixed_expenses=data.get("fixed_expenses", 12000),
        )

        result = run_agent_view(
            db=db,
            user=user_profile,
        )
        return jsonify(result)
    finally:
        db.close()


# ==================================================
# DB HEALTH
# ==================================================
@app.route("/health/db")
def db_health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"db": "connected"}
    except Exception as e:
        return {"db": "error", "detail": str(e)}, 500


# ==================================================
# RUN
# ==================================================
if __name__ == "__main__":
    app.run(debug=True)
