from flask import Flask, request, jsonify
import tempfile
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

from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity,
)

# ==================================================
# APP SETUP
# ==================================================
app = Flask(__name__)

# 🔐 JWT CORE CONFIG (ORDER MATTERS)
app.config["JWT_SECRET_KEY"] = "super-secret-key"  # MOVE TO ENV
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = False

# 🔴 REQUIRED: TELL JWT TO READ FROM HEADERS
app.config["JWT_TOKEN_LOCATION"] = ["headers"]
app.config["JWT_HEADER_NAME"] = "Authorization"
app.config["JWT_HEADER_TYPE"] = "Bearer"

jwt = JWTManager(app)

# ==================================================
# JWT DEBUGGING (CRITICAL DURING DEV)
# ==================================================
@jwt.invalid_token_loader
def invalid_token(reason):
    print("❌ INVALID JWT:", reason)
    return jsonify({"message": reason}), 422

@jwt.unauthorized_loader
def missing_token(reason):
    print("❌ MISSING JWT:", reason)
    return jsonify({"message": reason}), 401

# ==================================================
# CORS
# ==================================================
CORS(
    app,
    resources={r"/api/*": {"origins": [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5713",
    ]}},
    allow_headers=["Content-Type", "Authorization"],
)

# ==================================================
# AUTH HELPERS
# ==================================================
def get_current_user(db: Session) -> User | None:
    identity = get_jwt_identity()
    if not identity:
        return None
    return db.query(User).filter(User.id == int(identity)).first()


# ==================================================
# AUTH / USER
# ==================================================
@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    email = data.get("email")
    password = data.get("password")
    phone = data.get("phone")  # optional

    if not email or not password:
        return {"message": "email and password required"}, 400

    if len(password) < 8:
        return {"message": "password must be at least 8 characters"}, 400

    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == email).first():
            return {"message": "email already registered"}, 409

        user = User(email=email, phone=phone)
        user.set_password(password)

        db.add(user)
        db.commit()

        return {"status": "success"}
    finally:
        db.close()


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return {"message": "email and password required"}, 400

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()

        if not user or not user.check_password(password):
            return {"message": "invalid credentials"}, 401

        token = create_access_token(identity=str(user.id))


        return {
            "status": "success",
            "access_token": token,
            "user": {
                "id": user.id,
                "email": user.email,
            }
        }
    finally:
        db.close()

# ==================================================
# STATEMENT UPLOAD
# ==================================================
@app.route("/api/statement/parse", methods=["POST"])
@jwt_required()
def parse_statement_route():
    if "file" not in request.files:
        return {"message": "file required"}, 400

    file = request.files["file"]

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        file.save(tmp.name)
        pdf_path = tmp.name

    db = SessionLocal()
    try:
        user = get_current_user(db)
        if not user:
            return {"message": "user not found"}, 404

        result = parse_statement(
            db=db,
            pdf_path=pdf_path,
            user_id=user.id,
        )
        return jsonify(result)
    finally:
        db.close()

# ==================================================
# ANALYTICS
# ==================================================
@app.route("/api/statement/analytics", methods=["GET"])
@jwt_required()
def analytics_route():
    month = request.args.get("month")
    period = request.args.get("period")

    start_date = end_date = None

    if month:
        start_date = datetime.strptime(month, "%Y-%m")
        end_date = start_date + relativedelta(months=1)
    elif period:
        months = int(period.replace("m", ""))
        end_date = datetime.utcnow()
        start_date = end_date - relativedelta(months=months)

    db = SessionLocal()
    try:
        user = get_current_user(db)
        if not user:
            return {"message": "user not found"}, 404

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
# INSIGHTS
# ==================================================
@app.route("/api/statement/insights", methods=["GET"])
@jwt_required()
def insights_route():
    force_refresh = request.args.get("force_refresh") == "true"

    db = SessionLocal()
    try:
        user = get_current_user(db)
        if not user:
            return {"message": "user not found"}, 404

        result = generate_insights_view(
            db=db,
            user_id=user.id,
            force_refresh=force_refresh,
        )
        return jsonify(result)
    finally:
        db.close()

# ==================================================
# AGENT RECOMMENDATIONS
# ==================================================
@app.route("/api/agent/recommendations", methods=["POST"])
@jwt_required()
def agent_route():
    data = request.get_json(silent=True) or {}

    db = SessionLocal()
    try:
        user = get_current_user(db)
        if not user:
            return {"message": "user not found"}, 404

        raw_goals = data.get("goals")

        if raw_goals:
            goals = parse_user_goals(raw_goals)
        else:
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
# GOALS API
# ==================================================
@app.route("/api/goals", methods=["GET"])
@jwt_required()
def get_goals():
    db = SessionLocal()
    try:
        user = get_current_user(db)
        if not user:
            return {"message": "user not found"}, 404

        goals = (
            db.query(FinancialGoal)
            .filter(
                FinancialGoal.user_id == user.id,
                FinancialGoal.is_active.is_(True),
            )
            .order_by(FinancialGoal.created_at.desc())
            .all()
        )

        return {
            "status": "success",
            "goals": [
                {
                    "id": g.id,
                    "name": g.name,
                    "target_amount": g.target_amount,
                    "deadline": g.deadline.isoformat(),
                    "priority": g.priority,
                }
                for g in goals
            ],
        }
    finally:
        db.close()


@app.route("/api/goals", methods=["POST"])
@jwt_required()
def create_goals():
    data = request.get_json(silent=True) or {}
    raw_goals = data.get("goals")

    if not isinstance(raw_goals, list):
        return {"message": "goals list required"}, 400

    db = SessionLocal()
    try:
        user = get_current_user(db)
        if not user:
            return {"message": "user not found"}, 404

        parsed = parse_user_goals(raw_goals)

        for g in parsed:
            exists = db.query(FinancialGoal).filter(
                FinancialGoal.user_id == user.id,
                FinancialGoal.name == g.name,
                FinancialGoal.is_active.is_(True),
            ).first()

            if not exists:
                db.add(FinancialGoal(
                    user_id=user.id,
                    name=g.name,
                    target_amount=g.target_amount,
                    deadline=g.deadline,
                    priority=g.priority,
                ))

        db.commit()
        return {"status": "success"}
    finally:
        db.close()


@app.route("/api/goals/<int:goal_id>", methods=["DELETE"])
@jwt_required()
def delete_goal(goal_id):
    db = SessionLocal()
    try:
        user = get_current_user(db)
        if not user:
            return {"message": "user not found"}, 404

        goal = db.query(FinancialGoal).filter(
            FinancialGoal.id == goal_id,
            FinancialGoal.user_id == user.id,
            FinancialGoal.is_active.is_(True),
        ).first()

        if not goal:
            return {"message": "goal not found"}, 404

        goal.is_active = False
        db.commit()
        return {"status": "success"}
    finally:
        db.close()

# ==================================================
# TRANSACTIONS (WITH CONFIDENCE)
# ==================================================
@app.route("/api/transactions", methods=["GET"])
@jwt_required()
def get_transactions():
    db = SessionLocal()
    try:
        user = get_current_user(db)
        if not user:
            return {"message": "user not found"}, 404

        rows = db.execute(text("""
            SELECT
                t.id,
                t.date,
                t.description,
                t.merchant,
                t.amount,
                t.category,
                t.category_confidence,
                t.category_source
            FROM transactions t
            JOIN statements s ON t.statement_id = s.id
            WHERE s.user_id = :user_id
            ORDER BY t.date DESC
        """), {"user_id": user.id}).fetchall()

        return {
            "transactions": [
                {
                    "id": r.id,
                    "date": r.date.isoformat(),
                    "description": r.description,
                    "merchant": r.merchant or r.description,
                    "amount": float(r.amount),
                    "category": r.category,
                    "confidence": float(r.category_confidence or 1.0),
                    "needs_review": (r.category_confidence or 1.0) < 0.70,
                    "source": r.category_source,
                }
                for r in rows
            ]
        }
    finally:
        db.close()
# ==================================================
# TRANSACTION EXPLAINABILITY
# ==================================================
@app.route("/api/transaction/explain/<int:tx_id>", methods=["GET"])
@jwt_required()
def explain_transaction(tx_id):
    db = SessionLocal()
    try:
        user = get_current_user(db)
        if not user:
            return {"message": "user not found"}, 404

        row = db.execute(text("""
            SELECT
                t.id,
                t.date,
                t.description,
                t.merchant,
                t.category,
                t.category_confidence,
                t.category_source,
                t.raw
            FROM transactions t
            JOIN statements s ON t.statement_id = s.id
            WHERE t.id = :tx_id
              AND s.user_id = :user_id
        """), {
            "tx_id": tx_id,
            "user_id": user.id
        }).fetchone()

        if not row:
            return {"message": "transaction not found"}, 404

        return {
            "transaction_id": row.id,
            "merchant": row.merchant or row.description,
            "category": row.category,
            "confidence": float(row.category_confidence or 1.0),
            "source": row.category_source,
            "decision_metadata": row.raw or {},
        }
    finally:
        db.close()
from analytics.merchant_memory import save_merchant_category

# ==================================================
# MANUAL TRANSACTION CORRECTION
# ==================================================
@app.route("/api/transaction/correct", methods=["POST"])
@jwt_required()
def correct_transaction():
    data = request.get_json(silent=True) or {}

    tx_id = data.get("transaction_id")
    merchant = data.get("merchant_normalized") or data.get("merchant")
    category = data.get("category")
    remember = data.get("remember", False)

    if not tx_id or not merchant or not category:
        return {"message": "missing required fields"}, 400

    db = SessionLocal()
    try:
        user = get_current_user(db)
        if not user:
            return {"message": "user not found"}, 404

        tx = db.execute(text("""
            SELECT t.id, t.merchant
            FROM transactions t
            JOIN statements s ON t.statement_id = s.id
            WHERE t.id = :tx_id
              AND s.user_id = :user_id
        """), {
            "tx_id": tx_id,
            "user_id": user.id
        }).fetchone()

        if not tx:
            return {"message": "transaction not found"}, 404

        db.execute(text("""
            UPDATE transactions
            SET
                merchant = :merchant,
                category = :category,
                category_confidence = 1.0,
                category_source = 'user'
            WHERE id = :tx_id
        """), {
            "merchant": merchant,
            "category": category,
            "tx_id": tx_id,
        })

        if remember:
            save_merchant_category(
                merchant=tx.merchant,
                category=category,
                confidence=1.0
            )

        db.commit()
        return {"status": "success"}
    finally:
        db.close()

# ==================================================
# HEALTH
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
