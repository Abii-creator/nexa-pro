from datetime import datetime
import re
from flask import Blueprint, jsonify, request, session
from app.extensions import db
from app.models import User, Guest, CheckinSettings
from app.audit import log_activity

checkin_bp = Blueprint("checkin", __name__)


def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)


def unauthorized():
    return jsonify({"error": "Unauthorized"}), 401


def forbidden(message="Check-in access required"):
    return jsonify({"error": message}), 403


def require_checkin_access():
    user = get_current_user()

    if not user:
        return None, unauthorized()

    if not user.is_active:
        return None, forbidden("Inactive or invalid account")

    role = (user.role or "").strip().lower()

    if role != "admin" and not user.can_checkin:
        return None, forbidden("Check-in access required")

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


def extract_guest_code(raw_text):
    value = (raw_text or "").strip()

    if not value:
        return ""

    upper_value = value.upper()

    match = re.search(r"GST-\d{5}", upper_value)
    if match:
        return match.group(0)

    return upper_value


@checkin_bp.get("/status")
def checkin_status():
    user, error = require_checkin_access()
    if error:
        return error

    settings = get_checkin_settings()
    return jsonify(settings.to_dict()), 200


@checkin_bp.get("/search")
def search_guests():
    user, error = require_checkin_access()
    if error:
        return error

    query_text = request.args.get("q", "").strip()

    if not query_text:
        return jsonify([]), 200

    like_term = f"%{query_text}%"

    guests = (
        Guest.query
        .filter(
            (Guest.code_no.ilike(like_term)) |
            (Guest.full_name.ilike(like_term)) |
            (Guest.phone.ilike(like_term)) |
            (Guest.email.ilike(like_term))
        )
        .order_by(Guest.id.desc())
        .limit(20)
        .all()
    )

    return jsonify([guest.to_dict() for guest in guests]), 200


@checkin_bp.post("/scan-checkin")
def scan_checkin():
    current_user, error = require_checkin_access()
    if error:
        return error

    try:
        settings = get_checkin_settings()

        if settings.is_checkin_locked():
            reason = settings.lock_reason()

            log_activity(
                actor_user_id=current_user.id,
                action="CHECK_IN_BLOCKED",
                description=f"QR check-in blocked. Reason: {reason}"
            )

            if reason == "manual":
                return jsonify({"error": "Check-in is manually locked"}), 403

            if reason == "event_ended":
                return jsonify({"error": "Check-in is closed because the event has ended"}), 403

            return jsonify({"error": "Check-in is locked"}), 403

        data = request.get_json() or {}
        raw_code = (data.get("code") or "").strip()

        if not raw_code:
            return jsonify({"error": "QR code or guest code is required"}), 400

        guest_code = extract_guest_code(raw_code)

        guest = Guest.query.filter_by(code_no=guest_code).first()

        if not guest:
            log_activity(
                actor_user_id=current_user.id,
                action="QR_CHECK_IN_GUEST_NOT_FOUND",
                description=f"QR check-in failed. Guest code not found: {guest_code}"
            )
            return jsonify({
                "error": "Guest not found",
                "searched_code": guest_code
            }), 404

        if guest.status == "Checked-in":
            log_activity(
                actor_user_id=current_user.id,
                action="CHECK_IN_DUPLICATE",
                description=f"Duplicate QR check-in attempt for '{guest.full_name}' ({guest.code_no})"
            )

            return jsonify({
                "message": "Guest already checked in",
                "already_checked_in": True,
                "guest": guest.to_dict()
            }), 200

        guest.status = "Checked-in"
        guest.checked_in_at = datetime.utcnow()

        db.session.commit()

        log_activity(
            actor_user_id=current_user.id,
            action="QR_CHECK_IN_GUEST",
            description=f"QR checked in guest '{guest.full_name}' ({guest.code_no})"
        )

        return jsonify({
            "message": "Guest checked in successfully",
            "already_checked_in": False,
            "guest": guest.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        print("QR CHECK-IN ERROR:", str(e))
        return jsonify({"error": "Failed to complete QR check-in"}), 500