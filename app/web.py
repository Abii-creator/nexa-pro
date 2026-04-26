from flask import Blueprint, render_template, session, redirect, url_for

web_bp = Blueprint("web", __name__)


@web_bp.get("/")
def home():
    if session.get("user_id"):
        return redirect(url_for("web.dashboard_page"))
    return render_template("login.html", title="Login", protected_page=False)


@web_bp.get("/login")
def login_page():
    if session.get("user_id"):
        return redirect(url_for("web.dashboard_page"))
    return render_template("login.html", title="Login", protected_page=False)


@web_bp.get("/dashboard")
def dashboard_page():
    if not session.get("user_id"):
        return redirect(url_for("web.login_page"))
    return render_template("dashboard.html", title="Dashboard", protected_page=True)


@web_bp.get("/guests")
def guests_page():
    if not session.get("user_id"):
        return redirect(url_for("web.login_page"))
    return render_template("guests.html", title="Guests", protected_page=True)


@web_bp.get("/checkin")
def checkin_page():
    if not session.get("user_id"):
        return redirect(url_for("web.login_page"))
    return render_template("checkin.html", title="Check-in", protected_page=True)


@web_bp.get("/users")
def users_page():
    if not session.get("user_id"):
        return redirect(url_for("web.login_page"))
    return render_template("users.html", title="Users", protected_page=True)


@web_bp.get("/admin")
def admin_page():
    if not session.get("user_id"):
        return redirect(url_for("web.login_page"))
    return render_template("admin.html", title="Admin", protected_page=True)