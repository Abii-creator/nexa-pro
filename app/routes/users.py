from flask import Blueprint, jsonify, request, session
from app.extensions import db
from app.models import User
from app.audit import log_activity

users_bp = Blueprint("users", __name__)


def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)


def unauthorized():
    return jsonify({"error": "Unauthorized"}), 401


def forbidden():
    return jsonify({"error": "Admin access required"}), 403


def require_admin():
    user = get_current_user()

    if not user:
        return None, unauthorized()

    if not user.is_active:
        return None, forbidden()

    if (user.role or "").strip().lower() != "admin":
        return None, forbidden()

    return user, None


@users_bp.get("/")
def list_users():
    current_user, error = require_admin()
    if error:
        return error

    search = request.args.get("search", "").strip()
    query = User.query

    if search:
        like = f"%{search}%"
        query = query.filter(
            (User.full_name.ilike(like)) |
            (User.username.ilike(like)) |
            (User.email.ilike(like)) |
            (User.role.ilike(like))
        )

    users = query.order_by(User.id.desc()).all()
    return jsonify([u.to_dict() for u in users]), 200


@users_bp.get("/<int:user_id>")
def get_user(user_id):
    current_user, error = require_admin()
    if error:
        return error

    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify(user.to_dict()), 200


@users_bp.post("/")
def create_user():
    current_user, error = require_admin()
    if error:
        return error

    try:
        data = request.get_json() or {}

        full_name = (data.get("full_name") or "").strip()
        username = (data.get("username") or "").strip()
        email = (data.get("email") or "").strip()
        password = (data.get("password") or "").strip()
        role = (data.get("role") or "User").strip()
        is_active = bool(data.get("is_active", True))

        if not full_name or not username or not email or not password:
            return jsonify({"error": "Full name, username, email, and password are required"}), 400

        if User.query.filter_by(username=username).first():
            return jsonify({"error": "Username already exists"}), 409

        if User.query.filter_by(email=email).first():
            return jsonify({"error": "Email already exists"}), 409

        user = User(
            full_name=full_name,
            username=username,
            email=email,
            role=role,
            is_active=is_active,
            can_manage_guests=False,
            can_checkin=bool(data.get("can_checkin", False)),
            can_manage_users=False,
            can_access_admin=bool(data.get("can_access_admin", False)),
            can_view_reports=bool(data.get("can_view_reports", False)),
        )

        if role == "Admin":
            user.apply_role_defaults()

        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        log_activity(
            actor_user_id=current_user.id,
            action="CREATE_USER",
            description=f"Created user '{username}' with role '{role}'"
        )

        return jsonify({
            "message": "User created successfully",
            "user": user.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        print("CREATE USER ERROR:", str(e))
        return jsonify({"error": "Failed to create user"}), 500


@users_bp.put("/<int:user_id>")
def update_user(user_id):
    current_user, error = require_admin()
    if error:
        return error

    try:
        user = User.query.get(user_id)

        if not user:
            return jsonify({"error": "User not found"}), 404

        data = request.get_json() or {}

        new_full_name = data.get("full_name") if data.get("full_name") is not None else user.full_name
        new_username = data.get("username") if data.get("username") is not None else user.username
        new_email = data.get("email") if data.get("email") is not None else user.email
        new_role = data.get("role") if data.get("role") is not None else user.role
        new_password = (data.get("password") or "").strip()

        new_full_name = new_full_name.strip() if isinstance(new_full_name, str) else user.full_name
        new_username = new_username.strip() if isinstance(new_username, str) else user.username
        new_email = new_email.strip() if isinstance(new_email, str) else user.email
        new_role = new_role.strip() if isinstance(new_role, str) else user.role

        if not new_full_name or not new_username or not new_email:
            return jsonify({"error": "Full name, username, and email are required"}), 400

        existing_username = User.query.filter(
            User.username == new_username,
            User.id != user.id
        ).first()

        if existing_username:
            return jsonify({"error": "Username already exists"}), 409

        existing_email = User.query.filter(
            User.email == new_email,
            User.id != user.id
        ).first()

        if existing_email:
            return jsonify({"error": "Email already exists"}), 409

        old_username = user.username

        user.full_name = new_full_name
        user.username = new_username
        user.email = new_email
        user.role = new_role
        user.is_active = bool(data.get("is_active", user.is_active))

        user.can_manage_guests = False
        user.can_manage_users = False
        user.can_checkin = bool(data.get("can_checkin", user.can_checkin))
        user.can_access_admin = bool(data.get("can_access_admin", user.can_access_admin))
        user.can_view_reports = bool(data.get("can_view_reports", user.can_view_reports))

        if new_role == "Admin":
            user.apply_role_defaults()

        if new_password:
            user.set_password(new_password)

        db.session.commit()

        log_activity(
            actor_user_id=current_user.id,
            action="UPDATE_USER",
            description=f"Updated user '{old_username}' to '{user.username}'"
        )

        return jsonify({
            "message": "User updated successfully",
            "user": user.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        print("UPDATE USER ERROR:", str(e))
        return jsonify({"error": "Failed to update user"}), 500


@users_bp.delete("/<int:user_id>")
def delete_user(user_id):
    current_user, error = require_admin()
    if error:
        return error

    try:
        user = User.query.get(user_id)

        if not user:
            return jsonify({"error": "User not found"}), 404

        if user.id == current_user.id:
            return jsonify({"error": "You cannot delete your own account"}), 400

        username = user.username

        db.session.delete(user)
        db.session.commit()

        log_activity(
            actor_user_id=current_user.id,
            action="DELETE_USER",
            description=f"Deleted user '{username}'"
        )

        return jsonify({"message": "User deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        print("DELETE USER ERROR:", str(e))
        return jsonify({"error": "Failed to delete user"}), 500