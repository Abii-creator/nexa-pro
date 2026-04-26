# app/routes/admin.py

from datetime import datetime
import os
import tempfile
import zipfile
from flask import Blueprint, jsonify, request, session, current_app, send_file
from app.extensions import db
from app.models import User, Guest, AuditLog, CheckinSettings, EventSettings
from app.audit import log_activity

admin_bp = Blueprint("admin", __name__)


def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)


def require_login():
    user = get_current_user()

    if not user:
        return None, (jsonify({"error": "Unauthorized"}), 401)

    if not user.is_active:
        return None, (jsonify({"error": "Inactive or invalid account"}), 403)

    return user, None


def require_admin():
    user, error = require_login()
    if error:
        return None, error

    if (user.role or "").strip().lower() != "admin":
        return None, (jsonify({"error": "Admin access required"}), 403)

    return user, None


def get_checkin_settings():
    settings = CheckinSettings.query.first()

    if not settings:
        settings = CheckinSettings(
            manual_lock=False,
            manual_lock_until=None,
            event_end_time=None
        )
        db.session.add(settings)
        db.session.commit()

    return settings


def get_event_settings_record():
    settings = EventSettings.query.first()

    if not settings:
        settings = EventSettings(
            event_name="Nexa Event Pro",
            client_name="Default Client",
            event_date="",
            venue="",
            logo_url=""
        )
        db.session.add(settings)
        db.session.commit()

    return settings


def get_sqlite_db_path():
    db_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")

    if not db_uri.startswith("sqlite:///"):
        return None

    db_file = db_uri.replace("sqlite:///", "", 1)

    if os.path.isabs(db_file):
        return db_file

    instance_path = current_app.instance_path
    candidate_instance = os.path.join(instance_path, db_file)

    if os.path.exists(candidate_instance):
        return candidate_instance

    candidate_root = os.path.join(current_app.root_path, db_file)

    if os.path.exists(candidate_root):
        return candidate_root

    return candidate_instance


@admin_bp.route("/dashboard-summary", methods=["GET"])
def dashboard_summary():
    user, error = require_login()
    if error:
        return error

    try:
        total_users = User.query.count()
        total_guests = Guest.query.count()
        checked_in = Guest.query.filter_by(status="Checked-in").count()
        pending = Guest.query.filter_by(status="Pending").count()

        settings = get_checkin_settings()
        event_settings = get_event_settings_record()

        latest = (
            Guest.query
            .filter(Guest.checked_in_at.isnot(None))
            .order_by(Guest.checked_in_at.desc())
            .limit(10)
            .all()
        )

        is_admin = (user.role or "").strip().lower() == "admin"

        return jsonify({
            "total_users": total_users,
            "total_guests": total_guests,
            "checked_in": checked_in,
            "pending": pending,
            "is_admin": is_admin,
            "checkin_settings": settings.to_dict(),
            "event_settings": event_settings.to_dict(),
            "latest_checkins": [
                {
                    "name": guest.full_name,
                    "code": guest.code_no,
                    "time": guest.checked_in_at.isoformat() if guest.checked_in_at else None,
                    "action": "Checked-in"
                }
                for guest in latest
            ]
        }), 200

    except Exception as e:
        print("DASHBOARD SUMMARY ERROR:", str(e))
        return jsonify({"error": "Failed to load dashboard summary"}), 500


@admin_bp.route("/event-settings", methods=["GET"])
def get_event_settings():
    user, error = require_admin()
    if error:
        return error

    settings = get_event_settings_record()
    return jsonify(settings.to_dict()), 200


@admin_bp.route("/event-settings", methods=["POST"])
def update_event_settings():
    user, error = require_admin()
    if error:
        return error

    try:
        data = request.get_json() or {}

        settings = get_event_settings_record()

        settings.event_name = (data.get("event_name") or "Nexa Event Pro").strip()
        settings.client_name = (data.get("client_name") or "").strip()
        settings.event_date = (data.get("event_date") or "").strip()
        settings.venue = (data.get("venue") or "").strip()
        settings.logo_url = (data.get("logo_url") or "").strip()

        db.session.commit()

        log_activity(
            actor_user_id=user.id,
            action="UPDATE_EVENT_SETTINGS",
            description=f"Updated event settings to '{settings.event_name}'"
        )

        return jsonify({
            "message": "Event settings updated successfully",
            "settings": settings.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        print("EVENT SETTINGS UPDATE ERROR:", str(e))
        return jsonify({"error": "Failed to update event settings"}), 500


@admin_bp.route("/checkin-lock", methods=["GET"])
def get_checkin_lock():
    user, error = require_login()
    if error:
        return error

    settings = get_checkin_settings()
    return jsonify(settings.to_dict()), 200


@admin_bp.route("/checkin-lock/manual-lock", methods=["POST"])
def manual_lock_checkin():
    user, error = require_admin()
    if error:
        return error

    try:
        data = request.get_json() or {}
        lock_until_raw = (data.get("manual_lock_until") or "").strip()

        settings = get_checkin_settings()
        settings.manual_lock = True

        if lock_until_raw:
            settings.manual_lock_until = datetime.fromisoformat(lock_until_raw)
        else:
            settings.manual_lock_until = None

        db.session.commit()

        log_activity(
            actor_user_id=user.id,
            action="MANUAL_LOCK_CHECKIN",
            description=f"Manual check-in lock enabled until {settings.manual_lock_until.isoformat() if settings.manual_lock_until else 'indefinite'}"
        )

        return jsonify({
            "message": "Manual check-in lock enabled",
            "settings": settings.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        print("MANUAL LOCK ERROR:", str(e))
        return jsonify({"error": "Failed to apply manual lock"}), 500


@admin_bp.route("/checkin-lock/unlock", methods=["POST"])
def manual_unlock_checkin():
    user, error = require_admin()
    if error:
        return error

    try:
        settings = get_checkin_settings()
        settings.manual_lock = False
        settings.manual_lock_until = None

        db.session.commit()

        log_activity(
            actor_user_id=user.id,
            action="UNLOCK_CHECKIN",
            description="Manual check-in lock disabled"
        )

        return jsonify({
            "message": "Check-in unlocked successfully",
            "settings": settings.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        print("UNLOCK ERROR:", str(e))
        return jsonify({"error": "Failed to unlock check-in"}), 500


@admin_bp.route("/checkin-lock/event-end-time", methods=["POST"])
def save_event_end_time():
    user, error = require_admin()
    if error:
        return error

    try:
        data = request.get_json() or {}
        event_end_time_raw = (data.get("event_end_time") or "").strip()

        settings = get_checkin_settings()

        if not event_end_time_raw:
            settings.event_end_time = None
            db.session.commit()

            log_activity(
                actor_user_id=user.id,
                action="CLEAR_EVENT_END_TIME",
                description="Auto lock event end time cleared"
            )

            return jsonify({
                "message": "Event end time cleared",
                "settings": settings.to_dict()
            }), 200

        settings.event_end_time = datetime.fromisoformat(event_end_time_raw)
        db.session.commit()

        log_activity(
            actor_user_id=user.id,
            action="SET_EVENT_END_TIME",
            description=f"Auto lock event end time set to {settings.event_end_time.isoformat()}"
        )

        return jsonify({
            "message": "Event end time saved",
            "settings": settings.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        print("SAVE EVENT END TIME ERROR:", str(e))
        return jsonify({"error": "Failed to save event end time"}), 500


@admin_bp.route("/profile", methods=["GET"])
def get_profile():
    user, error = require_admin()
    if error:
        return error

    return jsonify(user.to_dict()), 200


@admin_bp.route("/profile", methods=["PUT"])
def update_profile():
    user, error = require_admin()
    if error:
        return error

    try:
        data = request.get_json() or {}

        new_username = (data.get("username") or "").strip()
        old_password = (data.get("old_password") or "").strip()
        new_password = (data.get("new_password") or "").strip()

        if not new_username:
            return jsonify({"error": "Username is required"}), 400

        existing = User.query.filter(
            User.username == new_username,
            User.id != user.id
        ).first()

        if existing:
            return jsonify({"error": "Username already exists"}), 409

        old_username = user.username
        username_changed = new_username != user.username
        password_changed = False

        user.username = new_username

        if old_password or new_password:
            if not old_password or not new_password:
                return jsonify({"error": "Provide old and new password"}), 400

            if not user.check_password(old_password):
                return jsonify({"error": "Wrong old password"}), 401

            user.set_password(new_password)
            password_changed = True

        db.session.commit()
        session["username"] = user.username

        if username_changed or password_changed:
            log_activity(
                actor_user_id=user.id,
                action="UPDATE_ADMIN_PROFILE",
                description=f"Admin profile updated. Username changed from '{old_username}' to '{user.username}'"
            )

        return jsonify({
            "message": "Account updated",
            "username": user.username
        }), 200

    except Exception as e:
        db.session.rollback()
        print("PROFILE UPDATE ERROR:", str(e))
        return jsonify({"error": "Failed to update profile"}), 500


@admin_bp.route("/activity", methods=["GET"])
def admin_activity():
    user, error = require_admin()
    if error:
        return error

    try:
        logs = (
            AuditLog.query
            .order_by(AuditLog.id.desc())
            .limit(200)
            .all()
        )

        return jsonify({
            "logs": [log.to_dict() for log in logs]
        }), 200

    except Exception as e:
        print("ACTIVITY ERROR:", str(e))
        return jsonify({"error": "Failed to load activity"}), 500


@admin_bp.route("/backup/database", methods=["GET"])
def backup_database():
    user, error = require_admin()
    if error:
        return error

    db_path = get_sqlite_db_path()

    if not db_path or not os.path.exists(db_path):
        return jsonify({"error": "Database file not found"}), 404

    log_activity(
        actor_user_id=user.id,
        action="DOWNLOAD_DB_BACKUP",
        description="Downloaded SQLite database backup"
    )

    filename = f"nexa_event_pro_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

    return send_file(
        db_path,
        as_attachment=True,
        download_name=filename,
        mimetype="application/octet-stream"
    )


@admin_bp.route("/backup/qrcodes", methods=["GET"])
def backup_qrcodes():
    user, error = require_admin()
    if error:
        return error

    qr_folder = os.path.join(current_app.root_path, "static", "qrcodes")

    if not os.path.exists(qr_folder):
        return jsonify({"error": "QR codes folder not found"}), 404

    temp_dir = tempfile.gettempdir()
    zip_filename = f"nexa_qrcodes_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    zip_path = os.path.join(temp_dir, zip_filename)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(qr_folder):
            for file in files:
                if file.lower().endswith(".png"):
                    full_path = os.path.join(root, file)
                    arcname = os.path.relpath(full_path, qr_folder)
                    zipf.write(full_path, arcname)

    log_activity(
        actor_user_id=user.id,
        action="DOWNLOAD_QR_BACKUP",
        description="Downloaded QR codes ZIP backup"
    )

    return send_file(
        zip_path,
        as_attachment=True,
        download_name=zip_filename,
        mimetype="application/zip"
    )