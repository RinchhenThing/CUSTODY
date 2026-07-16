from flask import Flask, render_template, redirect, url_for, request, session, abort
from functools import wraps
import sqlite3
import os
from backup_db import DB_PATH, init_db

app = Flask(__name__)
app.secret_key = "CHANGE_ME_SECRET"

USERS = {
    "admin": {"password": "admin123", "role": "Admin"},
    "operator": {"password": "op123", "role": "Operator"},
    "auditor": {"password": "aud123", "role": "Auditor"},
}


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


def roles_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "user" not in roles:
                return redirect(url_for("login"))
            if session.get("role") not in roles:
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]
        user = USERS.get(u)
        if user and user["password"] == p:
            session["user"] = u
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))
        return "Invalid credentials", 401
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM files")
    backed_up = c.fetchone()[0]
    conn.close()
    return render_template(
        "dashboard.html",
        user=session["user"]
        role=session["role"]
        backed_up=backed_up,
    )


@app.route("/backup")
@login_required
def backups():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, rel_path, version, sha256, created_at FROM files ORDER BY created_at DESC LIMIT 100")
    rows = c.fetchall()
    conn.close()
    return render_template("backups.html", rows=rows)


@app.route("/admin/approve_restore", methods=["POST"])
@roles_required("Admin")
def approve_restore():
    rel_path = request.form["rel_path"]
    version = int(request.form["version"]
    from restore import restore_file
    dest = restore_file(rel_path, version)
    return f"Restore approved. Restored to {dest}"


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        init_db()
    app.run(host="0.0.0.0", port=5000)
