from flask import Flask, request, jsonify
import tempfile
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from db import engine, SessionLocal
from models import User
# ================================
# INSIGHTS DEPENDENCIES (REQUIRED)
# ================================
from models import Transaction, Statement

from pipeline.core import transactions_to_df

from analytics.metrics import compute_metrics_from_df
from analytics.categorization import category_summary

from agent.insights.financial_summary import generate_financial_summary
from agent.insights.transaction_patterns import generate_transaction_patterns
from agent.insights.category_insights import generate_category_insights

from pipeline.core import (
    parse_statement,
    compute_analytics,
    run_agent_view
)
from flask_cors import CORS

from agent.user_profile import UserProfile

from flask_cors import CORS

app = Flask(__name__)

CORS(
    app,
    resources={r"/api/*": {"origins": [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5713",
    ]}},
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# ==================================================
# USER HELPERS
# ==================================================
def get_or_create_user(
    db: Session,
    phone: str,
    email: str | None = None,
    password: str | None = None
) -> User:

    user = db.query(User).filter(User.phone == phone).first()

    if user:
        if email and not user.email:
            user.email = email

        if password and not user.password_hash:
            user.set_password(password)

        db.commit()
        db.refresh(user)
        return user

    user = User(phone=phone, email=email)

    if password:
        user.set_password(password)

    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# ==================================================
# 1️⃣ USER CREATE / FETCH
# ==================================================
@app.route("/api/user", methods=["POST"])
def create_or_get_user():
    data = request.get_json(silent=True) or {}

    phone = data.get("phone")
    email = data.get("email")
    password = data.get("password")

    if not phone:
        return jsonify({"status": "error", "message": "phone is required"}), 400

    if password and len(password) < 8:
        return jsonify({
            "status": "error",
            "message": "password must be at least 8 characters"
        }), 400

    db = SessionLocal()
    try:
        user = get_or_create_user(db, phone, email, password)

        return jsonify({
            "status": "success",
            "user": {
                "id": user.id,
                "phone": user.phone,
                "email": user.email,
                "has_password": bool(user.password_hash),
            },
        })
    finally:
        db.close()

@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    phone = data.get("phone")
    password = data.get("password")

    if not phone or not password:
        return jsonify({
            "status": "error",
            "message": "phone and password required"
        }), 400

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.phone == phone).first()

        if not user or not user.password_hash:
            return jsonify({
                "status": "error",
                "message": "Invalid credentials"
            }), 401

        if not user.check_password(password):
            return jsonify({
                "status": "error",
                "message": "Invalid credentials"
            }), 401

        return jsonify({
            "status": "success",
            "user": {
                "id": user.id,
                "phone": user.phone,
                "email": user.email,
            }
        })
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
# 3️⃣ ANALYTICS
# ==================================================
from datetime import datetime
from dateutil.relativedelta import relativedelta
from flask import request, jsonify

@app.route("/api/statement/analytics", methods=["GET"])
def analytics_route():
    phone = request.args.get("phone")
    month = request.args.get("month")     # e.g. 2026-01
    period = request.args.get("period")   # e.g. 3m, 6m, 12m

    if not phone:
        return jsonify({
            "status": "error",
            "message": "phone is required"
        }), 400

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.phone == phone).first()
        if not user:
            return jsonify({
                "status": "error",
                "message": "User not found"
            }), 404

        # ----------------------------------------------
        # Resolve date window
        # ----------------------------------------------
        start_date = None
        end_date = None

        # 📅 Monthly analytics (YYYY-MM)
        if month:
            try:
                start_date = datetime.strptime(month, "%Y-%m")
                end_date = start_date + relativedelta(months=1)
            except ValueError:
                return jsonify({
                    "status": "error",
                    "message": "Invalid month format. Use YYYY-MM"
                }), 400

        # 🔁 Rolling analytics (3m / 6m / 12m)
        elif period:
            if not period.endswith("m"):
                return jsonify({
                    "status": "error",
                    "message": "Invalid period. Use 3m, 6m, or 12m"
                }), 400

            try:
                months = int(period.replace("m", ""))
                if months not in (3, 6, 12):
                    raise ValueError
            except ValueError:
                return jsonify({
                    "status": "error",
                    "message": "Period must be 3m, 6m, or 12m"
                }), 400

            end_date = datetime.utcnow()
            start_date = end_date - relativedelta(months=months)

        # ----------------------------------------------
        # Compute analytics (single engine)
        # ----------------------------------------------
        result = compute_analytics(
            db=db,
            user_id=user.id,
            start_date=start_date,
            end_date=end_date,
        )

        return jsonify(result)

    finally:
        db.close()


# ==================================================
# 4️⃣ INSIGHTS (UPDATED – PARTIAL REFRESH SUPPORT)
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

        # --------------------------------------------------
        # Reuse analytics (single source of truth)
        # --------------------------------------------------
        analytics = compute_analytics(db=db, user_id=user.id)

        if analytics["status"] != "success":
            return jsonify({
                "status": "success",
                "financial_summary": {
                    "type": "system",
                    "model": None,
                    "content": "No data available yet."
                },
                "transaction_patterns": {
                    "type": "system",
                    "model": None,
                    "content": "No data available yet."
                },
                "category_insights": {
                    "type": "system",
                    "model": None,
                    "content": "No data available yet."
                },
            })

        metrics = analytics["metrics"]
        categories = analytics["categories"]

        # --------------------------------------------------
        # Build transaction sample (safe & minimal)
        # --------------------------------------------------
        txns = (
            db.query(Transaction)
            .join(Statement)
            .filter(Statement.user_id == user.id)
            .order_by(Transaction.date.desc())
            .limit(100)
            .all()
        )

        txn_sample = [
            {
                "date": t.date,
                "description": t.description,
                "category": t.category,
            }
            for t in txns
        ]

        # --------------------------------------------------
        # Generate insights (NO refresh flags)
        # --------------------------------------------------
        return jsonify({
            "status": "success",

            "financial_summary": generate_financial_summary(metrics),

            "transaction_patterns": generate_transaction_patterns(txn_sample),

            "category_insights": generate_category_insights(categories),
        })

    finally:
        db.close()

# ==================================================
# 5️⃣ AGENT RECOMMENDATIONS
# ==================================================
from agent.goal_parser import parse_user_goals


@app.route("/api/agent/recommendations", methods=["POST"])
def agent_route():
    data = request.get_json(silent=True) or {}

    phone = data.get("phone")
    if not phone:
        return jsonify({
            "status": "error",
            "message": "phone is required"
        }), 400

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.phone == phone).first()
        if not user:
            return jsonify({
                "status": "error",
                "message": "User not found"
            }), 404

        # ✅ Parse user-defined goals (OPTIONAL)
        raw_goals = data.get("goals")
        goals = parse_user_goals(raw_goals)

        result = run_agent_view(
            db=db,
            user_id=user.id,
            goals=goals
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
