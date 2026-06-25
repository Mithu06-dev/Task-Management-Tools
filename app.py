import os
import sqlite3
from datetime import datetime
from flask import Flask, g, redirect, render_template, request, session, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "task_manager.db")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")


def get_db():
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    os.makedirs(BASE_DIR, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'todo',
            priority TEXT NOT NULL DEFAULT 'medium',
            due_date TEXT DEFAULT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id)")
        conn.commit()


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    db = get_db()
    row = db.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    return row


def require_login():
    if not current_user():
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))


@app.route("/")
def index():
    user = current_user()
    if not user:
        return redirect(url_for("landing"))
    return redirect(url_for("dashboard"))


@app.route("/landing")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not username or not email or not password:
            flash("All fields are required.", "warning")
            return redirect(url_for("register"))
        if len(password) < 8:
            flash("Password must be at least 8 characters.", "warning")
            return redirect(url_for("register"))

        password_hash = generate_password_hash(password)
        created_at = datetime.utcnow().isoformat()

        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (username, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (username, email, password_hash, created_at),
            )
            db.commit()
        except sqlite3.IntegrityError:
            flash("Username or email already exists.", "warning")
            return redirect(url_for("register"))

        flash("Account created. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username_or_email = request.form.get("username_or_email", "").strip()
        password = request.form.get("password", "")

        if not username_or_email or not password:
            flash("All fields are required.", "warning")
            return redirect(url_for("login"))

        db = get_db()
        row = db.execute(
            "SELECT * FROM users WHERE username = ? OR email = ?",
            (username_or_email, username_or_email.lower()),
        ).fetchone()

        if not row or not check_password_hash(row["password_hash"], password):
            flash("Invalid credentials.", "danger")
            return redirect(url_for("login"))

        session["user_id"] = row["id"]
        session["username"] = row["username"]
        flash("Welcome back!", "success")
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "success")
    return redirect(url_for("landing"))


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    redirect_resp = require_login()
    if redirect_resp:
        return redirect_resp

    user = current_user()
    db = get_db()

    if request.method == "POST":
        action = request.form.get("action")

        if action == "create_task":
            title = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()
            status = request.form.get("status", "todo")
            priority = request.form.get("priority", "medium")
            due_date = request.form.get("due_date", "").strip() or None

            if not title:
                flash("Task title is required.", "warning")
            else:
                now = datetime.utcnow().isoformat()
                db.execute(
                    """
                    INSERT INTO tasks (user_id, title, description, status, priority, due_date, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (user["id"], title, description, status, priority, due_date, now, now),
                )
                db.commit()
                flash("Task added.", "success")

        elif action == "update_task":
            task_id = request.form.get("task_id")
            status = request.form.get("status")
            priority = request.form.get("priority")
            due_date = request.form.get("due_date", "").strip() or None
            description = request.form.get("description", "").strip()

            if task_id:
                now = datetime.utcnow().isoformat()
                db.execute(
                    """
                    UPDATE tasks
                    SET status = ?, priority = ?, due_date = ?, description = ?, updated_at = ?
                    WHERE id = ? AND user_id = ?
                    """,
                    (status, priority, due_date, description, now, int(task_id), user["id"]),
                )
                db.commit()
                flash("Task updated.", "success")

        elif action == "delete_task":
            task_id = request.form.get("task_id")
            if task_id:
                db.execute(
                    "DELETE FROM tasks WHERE id = ? AND user_id = ?",
                    (int(task_id), user["id"]),
                )
                db.commit()
                flash("Task deleted.", "success")

        return redirect(url_for("dashboard"))

    # Filters
    q = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "all")
    priority_filter = request.args.get("priority", "all")

    where = "WHERE user_id = ?"
    params = [user["id"]]

    if q:
        where += " AND (title LIKE ? OR description LIKE ?)"
        like = f"%{q}%"
        params.extend([like, like])

    if status_filter != "all":
        where += " AND status = ?"
        params.append(status_filter)

    if priority_filter != "all":
        where += " AND priority = ?"
        params.append(priority_filter)

    tasks = db.execute(
        f"""
        SELECT * FROM tasks
        {where}
        ORDER BY
            CASE status
                WHEN 'todo' THEN 1
                WHEN 'doing' THEN 2
                WHEN 'done' THEN 3
                ELSE 4
            END,
            due_date IS NULL,
            due_date ASC,
            created_at DESC
        """,
        params,
    ).fetchall()

    counts = db.execute(
        """
        SELECT status, COUNT(*) AS c
        FROM tasks
        WHERE user_id = ?
        GROUP BY status
        """,
        (user["id"],),
    ).fetchall()
    count_map = {r["status"]: r["c"] for r in counts}

    return render_template(
        "dashboard.html",
        user=user,
        tasks=tasks,
        count_map=count_map,
        q=q,
        status_filter=status_filter,
        priority_filter=priority_filter,
    )


@app.route("/profile", methods=["GET", "POST"])
def profile():
    redirect_resp = require_login()
    if redirect_resp:
        return redirect_resp

    user = current_user()
    db = get_db()

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()

        if not username or not email:
            flash("Username and email are required.", "warning")
            return redirect(url_for("profile"))

        try:
            db.execute(
                "UPDATE users SET username = ?, email = ? WHERE id = ?",
                (username, email, user["id"]),
            )
            db.commit()
            session["username"] = username
            flash("Profile updated.", "success")
        except sqlite3.IntegrityError:
            flash("Username or email already exists.", "warning")

        return redirect(url_for("profile"))

    return render_template("profile.html", user=user)


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)

