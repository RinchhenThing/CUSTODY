from flask import Flask, render_template, redirect, url_for, request, session, jsonify, render_template
import backup_db
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps


app = Flask(__name__)


@app.route("/api/backups", methods=["GET"])
def backups_api():
    rows = backup_db.list_files(limit=100)
    return jsonify(rows)


app.secret_key = "change_this_to_a_random_secret"


USERS = {
    "admin": {
        "password_hash": generate_password_hash("admin123"),
        "role": "Admin",
    },
    "analyst": {
        "password_hash": generate_password_hash("admin123"),
        "role": "Analyst",
    },
}


def current_user():
    username = session.get("username")
    if not username:
        return None
    user = USERS.get(username)
    if not user:
        return None
    return {"username": username, "role": user["role"]}

def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user:
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapper


def role_required(*roles):
    """Restrict access to users whose roloe is in roles."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                return redirect(url_for("login"))
            if user["role"] not in roles:
                return "Forbidden: insufficient permissions", 403
            return view_func(*args, **kwargs)
        return wrapper
    return decorator


@app.route("/")
@login_required
def dashboard():
    user = current_user()
    dummy_stats = {
        "total_backups":12,
    }


    return render_template(
        "dashboard.html",
        user=user["username"],
        role=user["role"],
        backed_up=dummy_stats["total_backups"],
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username", "")
    password = request.form.get("password", "")


    user = USERS.get(username)
    if not user or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid username or password"), 401
    session["username"] = username
    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    return "Logged out"


@app.route("/backups", methods=["GET"])
@login_required
def backups():
    rows = [
        (1, "docs/report.docx", 1, "abc123...", "2026-04-18 10:00"),
        (2, "docs/report.docx", 2, "def456...", "2026-04-19 09:00"),
    ]
    return render_template("backups.html", rows=rows)



@app.route("/restore_request", methods=["POST"])
@login_required
@role_required("Admin")
def restore_request():
    rel_path = request.form.get("rel_path")
    version = request.form.get("version")
    user = current_user()

    print(f"Restore request from {user['username']} for {rel_path} version {version}")

    return f"Restore request submitted for {rel_path} (version {version}) by {user['username']}"


@app.route("/status")
@login_required
def status():
    user = current_user()
    data = {
        "user": user,
        "backups": {
            "total": 12,
            "clean": 11,
            "quarantine": 3,
        },
        "last_backup": "2026-04-19 12:00",
    }
    return jsonify(data)



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)



