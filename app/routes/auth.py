from flask import Blueprint, request, jsonify, session, redirect, url_for
from app.models import User
from app.audit import log_activity

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON data received"}), 400

        username = (data.get("username") or "").strip()
        password = (data.get("password") or "").strip()

        if not username or not password:
            return jsonify({"error": "Username and password required"}), 400

        user = User.query.filter_by(username=username).first()

        if not user:
            log_activity(
                actor_user_id=None,
                action="LOGIN_FAIL",
                description=f"Failed login attempt for unknown username '{username}'"
            )
            return jsonify({"error": "User not found"}), 401

        if not user.check_password(password):
            log_activity(
                actor_user_id=user.id,
                action="LOGIN_FAIL",
                description=f"Wrong password attempt for username '{username}'"
            )
            return jsonify({"error": "Wrong password"}), 401

        if not user.is_active:
            log_activity(
                actor_user_id=user.id,
                action="LOGIN_FAIL",
                description=f"Inactive account login attempt for username '{username}'"
            )
            return jsonify({"error": "User account is inactive"}), 403

        session["user_id"] = user.id
        session["username"] = user.username
        session["role"] = user.role

        log_activity(
            actor_user_id=user.id,
            action="LOGIN_SUCCESS",
            description=f"User '{user.username}' logged in"
        )

        return jsonify({
            "message": "Login successful",
            "redirect": "/dashboard",
            "user": user.to_dict()
        }), 200

    except Exception as e:
        print("LOGIN ERROR:", str(e))
        return jsonify({"error": "Server error"}), 500


@auth_bp.route("/logout", methods=["GET"])
def logout():
    user_id = session.get("user_id")
    username = session.get("username")

    if user_id:
        log_activity(
            actor_user_id=user_id,
            action="LOGOUT",
            description=f"User '{username}' logged out"
        )

    session.clear()
    return redirect(url_for("web.login_page"))


@auth_bp.route("/me", methods=["GET"])
def me():
    user_id = session.get("user_id")

    if not user_id:
        return jsonify({"error": "Unauthorized", "user": None}), 401

    user = User.query.get(user_id)

    if not user:
        session.clear()
        return jsonify({"error": "Unauthorized", "user": None}), 401

    return jsonify(user.to_dict()), 200