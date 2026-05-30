from flask import Flask, render_template, request, redirect, session
import sqlite3
import bcrypt

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DATABASE ----------------

def get_db():
    conn = sqlite3.connect("expense.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        budget REAL DEFAULT 0
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS expenses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        amount REAL,
        category TEXT,
        payment_mode TEXT,
        date TEXT,
        recurring INTEGER DEFAULT 0
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS categories(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        budget REAL DEFAULT 0
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS goals(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        target REAL,
        saved REAL DEFAULT 0
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS goal_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        date TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- HOME ----------------

@app.route("/")
def home():
    return render_template("auth.html")

# ---------------- SIGNUP ----------------

@app.route("/signup", methods=["POST"])
def signup():
    conn = get_db()
    c = conn.cursor()

    hashed = bcrypt.hashpw(
        request.form["password"].encode(),
        bcrypt.gensalt()
    ).decode()

    try:
        c.execute("INSERT INTO users(name,email,password) VALUES(?,?,?)",
                  (request.form["name"], request.form["email"], hashed))
        conn.commit()
    except:
        return "❌ Email already exists"

    conn.close()
    return redirect("/")

# ---------------- LOGIN ----------------

@app.route("/login", methods=["POST"])
def login():
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE email=?", (request.form["email"],))
    user = c.fetchone()
    conn.close()

    if user and bcrypt.checkpw(request.form["password"].encode(), user["password"].encode()):
        session["user_id"] = user["id"]
        session["username"] = user["name"]
        return redirect("/dashboard")

    return "❌ Login Failed"

# ---------------- DASHBOARD ----------------

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user_id" not in session:
        return redirect("/")

    conn = get_db()
    c = conn.cursor()
    user_id = session["user_id"]

    # ---------------- SAVE BUDGET ----------------
    if request.method == "POST":
        budget = request.form.get("budget")
        if budget:
            c.execute("UPDATE users SET budget=? WHERE id=?",
                      (budget, user_id))
            conn.commit()

    # ---------------- GET USER ----------------
    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = c.fetchone()

    total_budget = user["budget"] if user["budget"] else 0

    # ---------------- FILTER (MONTH) ----------------
    month = request.args.get("month")

    query = """
        SELECT category, SUM(amount) as total
        FROM expenses
        WHERE user_id=?
    """
    params = [user_id]

    if month:
        query += " AND strftime('%m', date)=?"
        params.append(month)

    query += " GROUP BY category"

    c.execute(query, params)
    data = c.fetchall()

    # ---------------- TOTAL SPENT ----------------
    total_spent = sum([row["total"] for row in data]) if data else 0
    remaining = total_budget - total_spent

    # ---------------- CHART ----------------
    labels = [row["category"] for row in data]
    values = [row["total"] for row in data]

    # ---------------- AI INSIGHTS ----------------
    insights = []
    notifications = []

    if total_budget > 0:

        percent_used = (total_spent / total_budget) * 100

        if percent_used >= 100:
            insights.append("🚨 You have exceeded your budget!")
            notifications.append("❌ Budget exceeded! Reduce spending immediately.")

        elif percent_used >= 80:
            insights.append("⚠️ You are close to your budget limit.")
            notifications.append("⚠️ Warning: You’ve used over 80% of your budget.")

        else:
            insights.append("✅ Your spending is under control.")

        if remaining > 0:
            insights.append(f"💡 You can still spend ₹{int(remaining)} wisely.")
        else:
            insights.append("❌ No remaining budget.")

    else:
        insights.append("⚠️ Please set a monthly budget.")

    # ---------------- CLOSE ----------------
    conn.close()

    return render_template(
        "dashboard.html",
        user=user,
        total_budget=total_budget,
        total_spent=total_spent,
        remaining=remaining,
        labels=labels,
        values=values,
        insights=insights,
        notifications=notifications
    )

# ---------------- EXPENSES ----------------
@app.route("/expenses", methods=["GET"])
def expenses():
    if "user_id" not in session:
        return redirect("/")

    conn = get_db()
    c = conn.cursor()

    user_id = session["user_id"]

    # GET FILTER VALUES (SAFE DEFAULTS)
    search = request.args.get("search", "").strip()
    date = request.args.get("date", "")
    month = request.args.get("month", "")
    payment = request.args.get("payment", "")

    # BASE QUERY
    query = "SELECT * FROM expenses WHERE user_id=?"
    params = [user_id]

    # 🔍 SEARCH
    if search:
        query += " AND (title LIKE ? OR category LIKE ?)"
        params.append(f"%{search}%")
        params.append(f"%{search}%")

    # 📅 DATE FILTER
    if date:
        query += " AND date=?"
        params.append(date)

    # 📆 MONTH FILTER
    if month:
        query += " AND strftime('%m', date)=?"
        params.append(month)

    # 💳 PAYMENT FILTER
    if payment:
        query += " AND payment_mode=?"
        params.append(payment)

    # SORT
    query += " ORDER BY date DESC"

    # EXECUTE
    c.execute(query, params)
    expenses = c.fetchall()

    # GET CATEGORIES
    c.execute("SELECT name FROM categories WHERE user_id=?", (user_id,))
    categories = c.fetchall()

    conn.close()

    return render_template(
        "expenses.html",
        expenses=expenses,
        categories=categories
    )

# ---------------- ADD EXPENSE ----------------

@app.route("/add_expense", methods=["POST"])
def add_expense():
    if "user_id" not in session:
        return redirect("/")

    conn = get_db()
    c = conn.cursor()

    c.execute("""
        INSERT INTO expenses(user_id,title,amount,category,payment_mode,date)
        VALUES(?,?,?,?,?,?)
    """, (
        session["user_id"],
        request.form["title"],
        request.form["amount"],
        request.form["category"],
        request.form["payment"],
        request.form["date"]
    ))

    conn.commit()
    conn.close()

    return redirect("/expenses")

@app.route("/edit_expense/<int:id>", methods=["GET", "POST"])
def edit_expense(id):
    if "user_id" not in session:
        return redirect("/")

    conn = get_db()
    c = conn.cursor()

    # GET EXPENSE
    expense = c.execute("""
        SELECT * FROM expenses
        WHERE id=? AND user_id=?
    """, (id, session["user_id"])).fetchone()

    # IF NOT FOUND
    if not expense:
        conn.close()
        return redirect("/expenses")

    # UPDATE
    if request.method == "POST":
        c.execute("""
            UPDATE expenses
            SET title=?, amount=?, category=?, payment_mode=?, date=?
            WHERE id=? AND user_id=?
        """, (
            request.form["title"],
            request.form["amount"],
            request.form["category"],
            request.form["payment"],
            request.form["date"],
            id,
            session["user_id"]
        ))

        conn.commit()
        conn.close()
        return redirect("/expenses")

    # GET categories
    categories = c.execute("""
        SELECT name FROM categories WHERE user_id=?
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template("edit_expense.html", expense=expense, categories=categories)

@app.route("/delete_expense/<int:id>")
def delete_expense(id):
    if "user_id" not in session:
        return redirect("/")

    conn = get_db()
    c = conn.cursor()

    c.execute("""
        DELETE FROM expenses
        WHERE id=? AND user_id=?
    """, (id, session["user_id"]))

    conn.commit()
    conn.close()

    return redirect("/expenses")

# ---------------- CATEGORIES ----------------

@app.route("/categories")
def categories_page():
    if "user_id" not in session:
        return redirect("/")

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM categories WHERE user_id=?", (session["user_id"],))
    categories = c.fetchall()

    c.execute("""
        SELECT category, SUM(amount) as total
        FROM expenses
        WHERE user_id=?
        GROUP BY category
    """, (session["user_id"],))

    spent_map = {row["category"]: row["total"] for row in c.fetchall()}

    updated = []
    for cat in categories:
        d = dict(cat)
        d["spent"] = spent_map.get(d["name"], 0)
        updated.append(d)

    conn.close()

    return render_template("categories.html", categories=updated)

@app.route("/add_category", methods=["POST"])
def add_category():
    if "user_id" not in session:
        return redirect("/")

    conn = get_db()
    c = conn.cursor()

    c.execute("""
        INSERT INTO categories(user_id, name, budget)
        VALUES (?, ?, ?)
    """, (
        session["user_id"],
        request.form["name"],
        request.form["budget"]
    ))

    conn.commit()
    conn.close()

    return redirect("/categories")

@app.route("/delete_category/<int:id>")
def delete_category(id):
    if "user_id" not in session:
        return redirect("/")

    conn = get_db()
    c = conn.cursor()

    c.execute("""
        DELETE FROM categories
        WHERE id=? AND user_id=?
    """, (id, session["user_id"]))

    conn.commit()
    conn.close()

    return redirect("/categories")

# ---------------- ANALYTICS ----------------

@app.route("/analytics")
def analytics():
    if "user_id" not in session:
        return redirect("/")

    conn = get_db()
    c = conn.cursor()

    c.execute("""
        SELECT category, SUM(amount) as total
        FROM expenses
        WHERE user_id=?
        GROUP BY category
    """, (session["user_id"],))

    data = c.fetchall()

    labels = [row["category"] for row in data]
    values = [row["total"] for row in data]

    conn.close()

    return render_template("analytics.html", labels=labels, values=values)

# ---------------- GOALS ----------------

@app.route("/goals", methods=["GET", "POST"])
def goals():
    if "user_id" not in session:
        return redirect("/")

    conn = get_db()
    c = conn.cursor()
    user_id = session["user_id"]

    # GET GOAL
    c.execute("SELECT * FROM goals WHERE user_id=?", (user_id,))
    goal = c.fetchone()

    # ---------------- POST ----------------
    if request.method == "POST":

        # ✅ UPDATE TARGET
        if "target" in request.form:
            target = request.form.get("target")

            if goal:
                c.execute("UPDATE goals SET target=? WHERE user_id=?",
                          (target, user_id))
            else:
                c.execute("INSERT INTO goals(user_id,target,saved) VALUES (?,?,0)",
                          (user_id, target))

        # ✅ ADD SAVINGS
        elif "amount" in request.form:
            amount = float(request.form.get("amount"))

            if goal:
                c.execute("UPDATE goals SET saved = saved + ? WHERE user_id=?",
                          (amount, user_id))
            else:
                c.execute("INSERT INTO goals(user_id,target,saved) VALUES (?,?,?)",
                          (user_id, 0, amount))

            # ✅ SAVE HISTORY
            c.execute("""
                INSERT INTO goal_history(user_id, amount, date)
                VALUES (?, ?, date('now'))
            """, (user_id, amount))

        conn.commit()

        # 🔥 IMPORTANT: prevent resubmission
        return redirect("/goals")
    

    # ---------------- GET UPDATED DATA ----------------
    c.execute("SELECT * FROM goals WHERE user_id=?", (user_id,))
    goal = c.fetchone()

    c.execute("""
        SELECT * FROM goal_history
        WHERE user_id=?
        ORDER BY id DESC
    """, (user_id,))
    history = c.fetchall()

    conn.close()

    return render_template("goals.html", goal=goal, history=history)

# ---------------- RESET GOAL ----------------
@app.route("/reset_goal", methods=["POST"])
def reset_goal():
    if "user_id" not in session:
        return redirect("/")

    conn = get_db()
    c = conn.cursor()
    user_id = session["user_id"]

    # ✅ Reset saved amount
    c.execute("UPDATE goals SET saved = 0 WHERE user_id=?", (user_id,))

    # ✅ Delete all history
    c.execute("DELETE FROM goal_history WHERE user_id=?", (user_id,))

    conn.commit()
    conn.close()

    return redirect("/goals")

@app.route("/delete_saving/<int:id>")
def delete_saving(id):
    if "user_id" not in session:
        return redirect("/")

    conn = get_db()
    c = conn.cursor()
    user_id = session["user_id"]

    saving = c.execute("""
        SELECT amount FROM goal_history
        WHERE id=? AND user_id=?
    """, (id, user_id)).fetchone()

    if saving:
        amount = saving["amount"]

        # subtract from total saved
        c.execute("UPDATE goals SET saved = saved - ? WHERE user_id=?",
                  (amount, user_id))

        # delete record
        c.execute("DELETE FROM goal_history WHERE id=? AND user_id=?",
                  (id, user_id))

    conn.commit()
    conn.close()

    return redirect("/goals")

# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.context_processor
def inject_user():
    if "user_id" in session:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE id=?", (session["user_id"],))
        user = c.fetchone()
        return dict(user=user)
    return dict(user=None)

# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(debug=True)