import os
from datetime import datetime
from functools import wraps

from flask import Flask, request, jsonify, render_template, redirect, url_for, session, g
from werkzeug.security import generate_password_hash, check_password_hash

from db import get_db, init_db, DB_PATH
from ml.predict import predict_category

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
init_db()

CATEGORIES = ["Food", "Transport", "Shopping", "Bills", "Entertainment",
              "Health", "Education", "Other"]


# ---------------------------------------------------------------- helpers --

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api"):
                return jsonify({"error": "Not authenticated"}), 401
            return redirect(url_for("login_page"))
        return view(*args, **kwargs)
    return wrapped


def current_month():
    return datetime.now().strftime("%Y-%m")


# -------------------------------------------------------------- page routes

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard_page"))
    return redirect(url_for("login_page"))


@app.route("/register")
def register_page():
    return render_template("register.html")


@app.route("/login")
def login_page():
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))


@app.route("/dashboard-page")
@login_required
def dashboard_page():
    return render_template("dashboard.html", user_name=session.get("user_name"))


@app.route("/transactions-page")
@login_required
def transactions_page():
    return render_template("transactions.html", user_name=session.get("user_name"),
                            categories=CATEGORIES)


@app.route("/budgets-page")
@login_required
def budgets_page():
    return render_template("budgets.html", user_name=session.get("user_name"),
                            categories=CATEGORIES, current_month=current_month())


# --------------------------------------------------------- 9.1 Authentication

@app.route("/register", methods=["POST"])
def api_register():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not name or not email or not password:
        return jsonify({"error": "name, email and password are required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    db = get_db()
    existing = db.execute("SELECT user_id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        db.close()
        return jsonify({"error": "An account with that email already exists"}), 409

    password_hash = generate_password_hash(password)
    cur = db.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, password_hash),
    )
    db.commit()
    user_id = cur.lastrowid
    db.close()

    session["user_id"] = user_id
    session["user_name"] = name
    return jsonify({"message": "Registered successfully", "user_id": user_id}), 201


@app.route("/login", methods=["POST"])
def api_login():
    data = request.get_json(force=True)
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    db.close()

    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    session["user_id"] = user["user_id"]
    session["user_name"] = user["name"]
    return jsonify({"message": "Logged in", "user_id": user["user_id"], "name": user["name"]})


# ----------------------------------------------------- 9.2 Transaction mgmt

@app.route("/transactions", methods=["POST"])
@login_required
def add_transaction():
    data = request.get_json(force=True)
    date = data.get("date") or datetime.now().strftime("%Y-%m-%d")
    description = (data.get("description") or "").strip()
    amount = data.get("amount")
    ttype = data.get("type")
    category = data.get("category")

    if not description:
        return jsonify({"error": "description is required"}), 400
    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "amount must be a positive number"}), 400
    if ttype not in ("income", "expense"):
        return jsonify({"error": "type must be 'income' or 'expense'"}), 400

    predicted_category, confidence = (None, None)
    if ttype == "expense" and not category:
        predicted_category, confidence = predict_category(description)
        category = predicted_category
    elif not category:
        category = "Other"

    db = get_db()
    cur = db.execute(
        "INSERT INTO transactions (user_id, date, description, amount, type, category) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (session["user_id"], date, description, amount, ttype, category),
    )
    transaction_id = cur.lastrowid

    if predicted_category:
        db.execute(
            "INSERT INTO predictions (transaction_id, predicted_category, confidence) "
            "VALUES (?, ?, ?)",
            (transaction_id, predicted_category, confidence),
        )
    db.commit()
    db.close()

    return jsonify({
        "message": "Transaction added",
        "transaction_id": transaction_id,
        "category": category,
        "predicted": predicted_category is not None,
        "confidence": confidence,
    }), 201


@app.route("/transactions", methods=["GET"])
@login_required
def list_transactions():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM transactions WHERE user_id = ? ORDER BY date DESC, transaction_id DESC",
        (session["user_id"],),
    ).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@app.route("/transactions/<int:transaction_id>", methods=["PUT"])
@login_required
def update_transaction(transaction_id):
    data = request.get_json(force=True)
    db = get_db()
    row = db.execute(
        "SELECT * FROM transactions WHERE transaction_id = ? AND user_id = ?",
        (transaction_id, session["user_id"]),
    ).fetchone()
    if not row:
        db.close()
        return jsonify({"error": "Transaction not found"}), 404

    date = data.get("date", row["date"])
    description = data.get("description", row["description"])
    amount = data.get("amount", row["amount"])
    ttype = data.get("type", row["type"])
    category = data.get("category", row["category"])

    try:
        amount = float(amount)
    except (TypeError, ValueError):
        db.close()
        return jsonify({"error": "amount must be a number"}), 400

    db.execute(
        "UPDATE transactions SET date=?, description=?, amount=?, type=?, category=? "
        "WHERE transaction_id=? AND user_id=?",
        (date, description, amount, ttype, category, transaction_id, session["user_id"]),
    )
    db.commit()
    db.close()
    return jsonify({"message": "Transaction updated"})


@app.route("/transactions/<int:transaction_id>", methods=["DELETE"])
@login_required
def delete_transaction(transaction_id):
    db = get_db()
    db.execute(
        "DELETE FROM transactions WHERE transaction_id = ? AND user_id = ?",
        (transaction_id, session["user_id"]),
    )
    db.commit()
    db.close()
    return jsonify({"message": "Transaction deleted"})


# -------------------------------------------------- 9.3 AI expense categorization

@app.route("/predict-category", methods=["POST"])
@login_required
def api_predict_category():
    data = request.get_json(force=True)
    description = data.get("description", "")
    category, confidence = predict_category(description)
    return jsonify({"predicted_category": category, "confidence": round(confidence, 3)})


# ------------------------------------------------------------ 9.4 Budgets

@app.route("/budgets", methods=["POST"])
@login_required
def add_budget():
    data = request.get_json(force=True)
    month = data.get("month") or current_month()
    category = data.get("category")  # None/blank = overall monthly budget
    limit_amount = data.get("limit_amount")

    try:
        limit_amount = float(limit_amount)
        if limit_amount <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "limit_amount must be a positive number"}), 400

    db = get_db()
    existing = db.execute(
        "SELECT budget_id FROM budgets WHERE user_id=? AND month=? AND "
        "IFNULL(category,'')=IFNULL(?,'')",
        (session["user_id"], month, category),
    ).fetchone()

    if existing:
        db.execute("UPDATE budgets SET limit_amount=? WHERE budget_id=?",
                   (limit_amount, existing["budget_id"]))
    else:
        db.execute(
            "INSERT INTO budgets (user_id, month, category, limit_amount) VALUES (?, ?, ?, ?)",
            (session["user_id"], month, category, limit_amount),
        )
    db.commit()
    db.close()
    return jsonify({"message": "Budget saved"}), 201


@app.route("/budgets", methods=["GET"])
@login_required
def list_budgets():
    month = request.args.get("month") or current_month()
    db = get_db()
    budgets = db.execute(
        "SELECT * FROM budgets WHERE user_id=? AND month=?", (session["user_id"], month)
    ).fetchall()
    spent_rows = db.execute(
        "SELECT category, SUM(amount) as spent FROM transactions "
        "WHERE user_id=? AND type='expense' AND date LIKE ? GROUP BY category",
        (session["user_id"], f"{month}%"),
    ).fetchall()
    spent_by_category = {r["category"]: r["spent"] for r in spent_rows}
    total_spent = sum(spent_by_category.values())
    db.close()

    result = []
    for b in budgets:
        cat = b["category"]
        spent = spent_by_category.get(cat, total_spent if not cat else 0)
        limit_amount = b["limit_amount"]
        usage_pct = round((spent / limit_amount) * 100, 1) if limit_amount else 0
        result.append({
            "budget_id": b["budget_id"],
            "month": b["month"],
            "category": cat,
            "limit_amount": limit_amount,
            "spent": spent,
            "usage_pct": usage_pct,
            "status": "over" if usage_pct >= 100 else ("warning" if usage_pct >= 80 else "ok"),
        })
    return jsonify(result)


# --------------------------------------------------------- 9.5 Dashboard

@app.route("/dashboard", methods=["GET"])
@login_required
def api_dashboard():
    db = get_db()
    uid = session["user_id"]

    income = db.execute(
        "SELECT IFNULL(SUM(amount),0) as total FROM transactions WHERE user_id=? AND type='income'",
        (uid,),
    ).fetchone()["total"]
    expense = db.execute(
        "SELECT IFNULL(SUM(amount),0) as total FROM transactions WHERE user_id=? AND type='expense'",
        (uid,),
    ).fetchone()["total"]
    balance = income - expense

    category_rows = db.execute(
        "SELECT category, SUM(amount) as total FROM transactions "
        "WHERE user_id=? AND type='expense' GROUP BY category ORDER BY total DESC",
        (uid,),
    ).fetchall()

    monthly_rows = db.execute(
        "SELECT substr(date,1,7) as month, "
        "SUM(CASE WHEN type='income' THEN amount ELSE 0 END) as income, "
        "SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) as expense "
        "FROM transactions WHERE user_id=? GROUP BY month ORDER BY month",
        (uid,),
    ).fetchall()

    db.close()

    return jsonify({
        "total_income": income,
        "total_expense": expense,
        "balance": balance,
        "category_breakdown": [dict(r) for r in category_rows],
        "monthly_trend": [dict(r) for r in monthly_rows],
    })


# --------------------------------------------------- 9.6 / 9.7 Prediction & Insights

@app.route("/insights", methods=["GET"])
@login_required
def api_insights():
    db = get_db()
    uid = session["user_id"]

    monthly_rows = db.execute(
        "SELECT substr(date,1,7) as month, category, SUM(amount) as total "
        "FROM transactions WHERE user_id=? AND type='expense' "
        "GROUP BY month, category ORDER BY month",
        (uid,),
    ).fetchall()
    db.close()

    insights = []

    # --- 9.6 Spending prediction: simple average-of-last-3-months estimate ---
    months = {}
    for r in monthly_rows:
        months.setdefault(r["month"], {})[r["category"]] = r["total"]

    sorted_months = sorted(months.keys())
    if len(sorted_months) < 2:
        insights.append({
            "type": "prediction",
            "text": "Not enough historical data yet for a spending forecast. "
                    "Add a few more months of transactions to unlock this."
        })
    else:
        recent = sorted_months[-3:]
        totals = [sum(months[m].values()) for m in recent]
        estimate = round(sum(totals) / len(totals), 2)
        insights.append({
            "type": "prediction",
            "text": f"Based on your last {len(recent)} month(s), your estimated spending "
                    f"next month is around Rs. {estimate:,.2f}. This is an estimate, not a guarantee."
        })

        # month-over-month comparison per category (9.7 - identify high spending / patterns)
        if len(sorted_months) >= 2:
            prev, latest = sorted_months[-2], sorted_months[-1]
            for cat in months[latest]:
                prev_amt = months.get(prev, {}).get(cat, 0)
                latest_amt = months[latest][cat]
                if prev_amt > 0 and latest_amt > prev_amt * 1.2:
                    pct = round(((latest_amt - prev_amt) / prev_amt) * 100)
                    insights.append({
                        "type": "pattern",
                        "text": f"Your {cat} expenses increased by about {pct}% compared with last month."
                    })

    # --- 9.7 compare actual spending with budgets ---
    month = current_month()
    budgets = db_conn_budgets(uid, month)
    for b in budgets:
        if b["usage_pct"] >= 100:
            insights.append({
                "type": "budget",
                "text": f"You've exceeded your {b['category'] or 'overall'} budget for {month} "
                        f"(Rs. {b['spent']:,.2f} of Rs. {b['limit_amount']:,.2f})."
            })
        elif b["usage_pct"] >= 80:
            insights.append({
                "type": "budget",
                "text": f"You're at {b['usage_pct']}% of your {b['category'] or 'overall'} "
                        f"budget for {month} - consider slowing down."
            })

    insights.append({
        "type": "disclaimer",
        "text": "These insights are educational and generated automatically. "
                "They are not professional financial advice."
    })

    return jsonify(insights)


def db_conn_budgets(uid, month):
    """Reuses the same logic as list_budgets() but returns plain dicts (internal helper)."""
    db = get_db()
    budgets = db.execute(
        "SELECT * FROM budgets WHERE user_id=? AND month=?", (uid, month)
    ).fetchall()
    spent_rows = db.execute(
        "SELECT category, SUM(amount) as spent FROM transactions "
        "WHERE user_id=? AND type='expense' AND date LIKE ? GROUP BY category",
        (uid, f"{month}%"),
    ).fetchall()
    spent_by_category = {r["category"]: r["spent"] for r in spent_rows}
    total_spent = sum(spent_by_category.values())
    db.close()

    result = []
    for b in budgets:
        cat = b["category"]
        spent = spent_by_category.get(cat, total_spent if not cat else 0)
        limit_amount = b["limit_amount"]
        usage_pct = round((spent / limit_amount) * 100, 1) if limit_amount else 0
        result.append({
            "category": cat, "limit_amount": limit_amount,
            "spent": spent, "usage_pct": usage_pct,
        })
    return result
@app.route("/chatbot", methods=["GET"])
@login_required
def chatbot_page():
    return render_template(
        "chatbot.html",
        user_name=session.get("user_name")
    )
@app.route("/chatbot", methods=["POST"])
@login_required
def chatbot():
    data = request.get_json(force=True)
    message = (data.get("message") or "").lower().strip()

    if not message:
        return jsonify({"reply": "Please enter a question."})

    if "add" in message and "expense" in message:
        reply = "Go to Transactions, select Expense, enter the date, amount and description, then click Add Transaction."

    elif "edit" in message or "update" in message:
        reply = "Click the ✏️ button beside a transaction, change the details, and click Update Transaction."

    elif "delete" in message:
        reply = "Click the ✕ button beside a transaction to delete it."

    elif "budget" in message:
        reply = "You can create a monthly budget and set category-wise limits from the Budgets page."

    elif "category" in message:
        reply = "The system can automatically predict expense categories such as Food, Transport, Shopping, Bills and Entertainment."

    elif "dashboard" in message:
        reply = "The Dashboard shows your income, expenses, balance, category-wise spending and spending trends."

    elif "insight" in message:
        reply = "Insights analyze your spending patterns, budget usage and recent expenses."

    elif "hello" in message or "hi" in message:
        reply = "Hello! 👋 I'm your Finance Assistant. How can I help you?"

    elif "help" in message:
        reply = "I can help you with transactions, budgets, categories, dashboard and financial insights."

    else:
        reply = "I can help with transactions, budgets, categories, dashboard and financial insights."

    return jsonify({"reply": reply})


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        init_db()
    app.run(debug=True, port=5000)