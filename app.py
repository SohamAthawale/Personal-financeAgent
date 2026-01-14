from flask import Flask, request, jsonify
import tempfile
from pathlib import Path
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from db import engine, SessionLocal
from models import User, FinancialGoal

from agent.goal_parser import parse_user_goals
from pipeline.core import (
    parse_statement,
    compute_analytics,
    generate_insights_view,
    run_agent_view,
)

from flask_cors import CORS
from dateutil.relativedelta import relativedelta

# ==================================================
# APP SETUP
# ==================================================
app = Flask(__name__)

CORS(
    app,
    resources={r"/api/*": {"origins": [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5713",
    ]}},
    methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# ==================================================
# USER HELPERS
# ==================================================
def get_or_create_user(
    db: Session,
    phone: str,
    email: str | None = None,
    password: str | None = None,
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
# 1️⃣ USER CREATE / LOGIN
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

        if not user or not user.password_hash or not user.check_password(password):
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
@app.route("/api/statement/analytics", methods=["GET"])
def analytics_route():
    phone = request.args.get("phone")
    month = request.args.get("month")
    period = request.args.get("period")

    if not phone:
        return jsonify({"status": "error", "message": "phone is required"}), 400

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.phone == phone).first()
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404

        start_date = None
        end_date = None

        if month:
            start_date = datetime.strptime(month, "%Y-%m")
            end_date = start_date + relativedelta(months=1)

        elif period:
            months = int(period.replace("m", ""))
            end_date = datetime.utcnow()
            start_date = end_date - relativedelta(months=months)

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
# 4️⃣ INSIGHTS
# ==================================================
@app.route("/api/statement/insights", methods=["GET"])
def insights_route():
    phone = request.args.get("phone")
    force_refresh = request.args.get("force_refresh") == "true"

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
            force_refresh=force_refresh,
        )

        return jsonify(result)
    finally:
        db.close()

# ==================================================
# 5️⃣ AGENT RECOMMENDATIONS
# ==================================================
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

        # -----------------------------------------
        # ✅ GOALS SOURCE OF TRUTH
        # -----------------------------------------
        raw_goals = data.get("goals")

        if raw_goals:
            # Frontend-provided goals (optional override)
            goals = parse_user_goals(raw_goals)
        else:
            # 🔒 Load remembered goals from DB
            goals = [
                FinancialGoal(
                    name=g.name,
                    target_amount=g.target_amount,
                    deadline=g.deadline,
                    priority=g.priority,
                )
                for g in user.financial_goals
                if g.is_active
            ]

        result = run_agent_view(
            db=db,
            user_id=user.id,
            goals=goals,
        )

        return jsonify(result)

    finally:
        db.close()

# ==================================================
# 6️⃣ GOALS API (FINAL, NO DUPLICATES)
# ==================================================
@app.route("/api/goals", methods=["GET"], endpoint="api_get_goals")
def api_get_goals():
    phone = request.args.get("phone")
    if not phone:
        return jsonify({"status": "error", "message": "phone required"}), 400

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.phone == phone).first()
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404

        goals = (
            db.query(FinancialGoal)
            .filter(
                FinancialGoal.user_id == user.id,
                FinancialGoal.is_active.is_(True),
            )
            .order_by(FinancialGoal.created_at.desc())
            .all()
        )

        return jsonify({
            "status": "success",
            "goals": [
                {
                    "id": g.id,
                    "name": g.name,
                    "target_amount": g.target_amount,
                    "deadline": g.deadline.isoformat(),
                    "priority": g.priority,
                    "created_at": g.created_at.isoformat(),
                }
                for g in goals
            ],
        })
    finally:
        db.close()


@app.route("/api/goals", methods=["POST"], endpoint="api_create_goals")
def api_create_goals():
    data = request.get_json(silent=True) or {}
    phone = data.get("phone")
    raw_goals = data.get("goals")

    if not phone or not isinstance(raw_goals, list):
        return jsonify({"status": "error", "message": "phone and goals required"}), 400

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.phone == phone).first()
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404

        parsed = parse_user_goals(raw_goals)
        saved = 0

        for g in parsed:
            exists = (
                db.query(FinancialGoal)
                .filter(
                    FinancialGoal.user_id == user.id,
                    FinancialGoal.name == g.name,
                    FinancialGoal.is_active.is_(True),
                )
                .first()
            )
            if exists:
                continue

            db.add(
                FinancialGoal(
                    user_id=user.id,
                    name=g.name,
                    target_amount=g.target_amount,
                    deadline=g.deadline,
                    priority=g.priority,
                )
            )
            saved += 1

        db.commit()
        return jsonify({"status": "success", "saved": saved})
    finally:
        db.close()


@app.route("/api/goals/<int:goal_id>", methods=["DELETE"], endpoint="api_delete_goal")
def api_delete_goal(goal_id):
    phone = request.args.get("phone")
    if not phone:
        return jsonify({"status": "error", "message": "phone required"}), 400

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.phone == phone).first()
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404

        goal = (
            db.query(FinancialGoal)
            .filter(
                FinancialGoal.id == goal_id,
                FinancialGoal.user_id == user.id,
                FinancialGoal.is_active.is_(True),
            )
            .first()
        )

        if not goal:
            return jsonify({"status": "error", "message": "Goal not found"}), 404

        goal.is_active = False
        db.commit()

        return jsonify({"status": "success"})
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
