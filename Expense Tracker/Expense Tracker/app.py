from flask import Flask, render_template, request, redirect, session
import sqlite3
import bcrypt

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DATABASE SETUP ----------------

def init_db():
    conn = sqlite3.connect("expense.db")
    c = conn.cursor()

    # USERS TABLE
    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    """)

    # EXPENSES TABLE
    c.execute("""
    CREATE TABLE IF NOT EXISTS expenses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT NOT NULL,
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        date TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    # CATEGORIES TABLE
    c.execute("""
    CREATE TABLE IF NOT EXISTS categories(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
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
    name = request.form["name"]
    email = request.form["email"]
    password = request.form["password"]

    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    hashed_password = hashed_password.decode("utf-8")   # 🔥 important

    conn = sqlite3.connect("expense.db")
    c = conn.cursor()

    try:
        c.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            (name, email, hashed_password)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return "Email already exists!"

    conn.close()
    return redirect("/")

# ---------------- LOGIN ----------------

@app.route("/login", methods=["POST"])
def login():
    email = request.form["email"]
    password = request.form["password"]

    conn = sqlite3.connect("expense.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = c.fetchone()
    conn.close()

    if user:
        stored_password = user[3].encode("utf-8")

        if bcrypt.checkpw(password.encode("utf-8"), stored_password):
            session["user_id"] = user[0]
            session["username"] = user[1]
            return redirect("/dashboard")

    return render_template("auth.html", error="Invalid Email or Password")

# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/")

    conn = sqlite3.connect("expense.db")
    c = conn.cursor()

    # Total spent
    c.execute("SELECT SUM(amount) FROM expenses WHERE user_id = ?", (session["user_id"],))
    total_spent = c.fetchone()[0] or 0

    total_budget = 10000  # temporary fixed budget
    remaining = total_budget - total_spent

    # Category totals for chart
    c.execute("""
        SELECT category, SUM(amount)
        FROM expenses
        WHERE user_id = ?
        GROUP BY category
    """, (session["user_id"],))

    data = c.fetchall()
    conn.close()

    labels = [row[0] for row in data]
    values = [row[1] for row in data]

    return render_template(
        "dashboard.html",
        username=session["username"],
        total_budget=total_budget,
        total_spent=total_spent,
        remaining=remaining,
        labels=labels,
        values=values
    )
# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- Expense ----------------

@app.route("/expenses")
def expenses():
    if "user_id" not in session:
        return redirect("/")

    conn = sqlite3.connect("expense.db")
    c = conn.cursor()

    # Get user expenses
    c.execute("SELECT id, title, amount, category, date FROM expenses WHERE user_id = ?",
              (session["user_id"],))
    expenses = c.fetchall()

    # Get user categories
    c.execute("SELECT id, name FROM categories WHERE user_id = ?",
              (session["user_id"],))
    categories = c.fetchall()

    conn.close()

    return render_template("expenses.html",
                           expenses=expenses,
                           categories=categories)

# ---------------- Add Expense ----------------

@app.route("/add_expense", methods=["POST"])
def add_expense():
    if "user_id" not in session:
        return redirect("/")

    title = request.form["title"]
    amount = request.form["amount"]
    category = request.form["category"]
    date = request.form["date"]

    conn = sqlite3.connect("expense.db")
    c = conn.cursor()

    c.execute("""
        INSERT INTO expenses (user_id, title, amount, category, date)
        VALUES (?, ?, ?, ?, ?)
    """, (session["user_id"], title, amount, category, date))

    conn.commit()
    conn.close()

    return redirect("/expenses")

# ---------------- Delete Expense ----------------

@app.route("/delete_expense/<int:id>")
def delete_expense(id):
    if "user_id" not in session:
        return redirect("/")

    conn = sqlite3.connect("expense.db")
    c = conn.cursor()

    c.execute("DELETE FROM expenses WHERE id = ? AND user_id = ?",
              (id, session["user_id"]))

    conn.commit()
    conn.close()

    return redirect("/expenses")

# ---------------- Analytics ----------------

@app.route("/analytics")
def analytics():
    if "user_id" not in session:
        return redirect("/")

    conn = sqlite3.connect("expense.db")
    c = conn.cursor()

    c.execute("""
        SELECT category, SUM(amount)
        FROM expenses
        WHERE user_id = ?
        GROUP BY category
    """, (session["user_id"],))

    data = c.fetchall()
    conn.close()

    labels = [row[0] for row in data]
    values = [row[1] for row in data]

    return render_template("analytics.html",
                           labels=labels,
                           values=values)

# ---------------- Categories----------------
@app.route("/categories")
def categories():
    if "user_id" not in session:
        return redirect("/")

    conn = sqlite3.connect("expense.db")
    c = conn.cursor()

    c.execute("SELECT id, name FROM categories WHERE user_id = ?",
              (session["user_id"],))
    data = c.fetchall()
    conn.close()

    return render_template("categories.html", categories=data)

# ---------------- Add Categories----------------

@app.route("/add_category", methods=["POST"])
def add_category():
    if "user_id" not in session:
        return redirect("/")

    name = request.form["name"]

    conn = sqlite3.connect("expense.db")
    c = conn.cursor()

    c.execute("INSERT INTO categories (user_id, name) VALUES (?, ?)",
              (session["user_id"], name))

    conn.commit()
    conn.close()

    return redirect("/categories")

# ----------------Delete Categories----------------
@app.route("/delete_category/<int:id>")
def delete_category(id):
    if "user_id" not in session:
        return redirect("/")

    conn = sqlite3.connect("expense.db")
    c = conn.cursor()

    c.execute("DELETE FROM categories WHERE id = ? AND user_id = ?",
              (id, session["user_id"]))

    conn.commit()
    conn.close()

    return redirect("/categories")
# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(debug=True)