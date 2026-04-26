# app/routes/reports.py

import csv
import io
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, Response, session
from app.models import Guest, User, AuditLog

reports_bp = Blueprint("reports", __name__)


def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)


def unauthorized():
    return jsonify({"error": "Unauthorized"}), 401


def forbidden(message="Admin access required"):
    return jsonify({"error": message}), 403


def require_login():
    user = get_current_user()

    if not user:
        return None, unauthorized()

    if not user.is_active:
        return None, forbidden("Inactive or invalid account")

    return user, None


def require_admin():
    user, error = require_login()
    if error:
        return None, error

    if (user.role or "").strip().lower() != "admin":
        return None, forbidden("Admin access required")

    return user, None


def parse_date(value):
    if not value:
        return None

    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None


def apply_guest_filters(query):
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()
    start_date = parse_date(request.args.get("start_date", "").strip())
    end_date = parse_date(request.args.get("end_date", "").strip())

    if search:
        like = f"%{search}%"
        query = query.filter(
            (Guest.full_name.ilike(like)) |
            (Guest.phone.ilike(like)) |
            (Guest.email.ilike(like)) |
            (Guest.code_no.ilike(like)) |
            (Guest.organization.ilike(like)) |
            (Guest.title.ilike(like)) |
            (Guest.status.ilike(like))
        )

    if status:
        query = query.filter(Guest.status == status)

    if start_date:
        query = query.filter(Guest.created_at >= start_date)

    if end_date:
        query = query.filter(Guest.created_at < end_date + timedelta(days=1))

    return query


@reports_bp.get("/summary")
def reports_summary():
    current_user, error = require_admin()
    if error:
        return error

    total_guests = Guest.query.count()
    checked_in = Guest.query.filter_by(status="Checked-in").count()
    pending = Guest.query.filter_by(status="Pending").count()
    total_users = User.query.count()

    return jsonify({
        "total_guests": total_guests,
        "checked_in": checked_in,
        "pending": pending,
        "total_users": total_users
    }), 200


@reports_bp.get("/guests")
def reports_guests():
    current_user, error = require_login()
    if error:
        return error

    query = Guest.query
    query = apply_guest_filters(query)

    guests = query.order_by(Guest.id.desc()).limit(500).all()

    return jsonify([guest.to_dict() for guest in guests]), 200


@reports_bp.get("/status-chart")
def status_chart():
    current_user, error = require_admin()
    if error:
        return error

    checked_in = Guest.query.filter_by(status="Checked-in").count()
    pending = Guest.query.filter_by(status="Pending").count()

    return jsonify({
        "labels": ["Checked-in", "Pending"],
        "values": [checked_in, pending]
    }), 200


@reports_bp.get("/checkins-trend")
def checkins_trend():
    current_user, error = require_admin()
    if error:
        return error

    days = request.args.get("days", "7").strip()

    try:
        days = int(days)
    except ValueError:
        days = 7

    if days < 1:
        days = 7

    if days > 60:
        days = 60

    today = datetime.utcnow().date()
    start_day = today - timedelta(days=days - 1)

    labels = []
    values = []

    for i in range(days):
        day = start_day + timedelta(days=i)
        next_day = day + timedelta(days=1)

        count = Guest.query.filter(
            Guest.checked_in_at >= datetime.combine(day, datetime.min.time()),
            Guest.checked_in_at < datetime.combine(next_day, datetime.min.time())
        ).count()

        labels.append(day.strftime("%Y-%m-%d"))
        values.append(count)

    return jsonify({
        "labels": labels,
        "values": values
    }), 200


@reports_bp.get("/export/guests.csv")
def export_guests_csv():
    current_user, error = require_admin()
    if error:
        return error

    query = Guest.query
    query = apply_guest_filters(query)

    guests = query.order_by(Guest.id.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "ID",
        "Full Name",
        "Phone",
        "Email",
        "Organization",
        "Title",
        "Invitation Code",
        "Status",
        "Checked In At",
        "Created At"
    ])

    for guest in guests:
        writer.writerow([
            guest.id,
            guest.full_name or "",
            guest.phone or "",
            guest.email or "",
            guest.organization or "",
            guest.title or "",
            guest.code_no or "",
            guest.status or "",
            guest.checked_in_at.isoformat() if guest.checked_in_at else "",
            guest.created_at.isoformat() if guest.created_at else ""
        ])

    csv_data = output.getvalue()
    output.close()

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=guests_report.csv"
        }
    )


@reports_bp.get("/export/checkins.csv")
def export_checkins_csv():
    current_user, error = require_admin()
    if error:
        return error

    guests = (
        Guest.query
        .filter(Guest.checked_in_at.isnot(None))
        .order_by(Guest.checked_in_at.desc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "ID",
        "Full Name",
        "Phone",
        "Email",
        "Organization",
        "Title",
        "Invitation Code",
        "Status",
        "Checked In At"
    ])

    for guest in guests:
        writer.writerow([
            guest.id,
            guest.full_name or "",
            guest.phone or "",
            guest.email or "",
            guest.organization or "",
            guest.title or "",
            guest.code_no or "",
            guest.status or "",
            guest.checked_in_at.isoformat() if guest.checked_in_at else ""
        ])

    csv_data = output.getvalue()
    output.close()

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=checkins_report.csv"
        }
    )


@reports_bp.get("/export/audit-logs.csv")
def export_audit_logs_csv():
    current_user, error = require_admin()
    if error:
        return error

    logs = AuditLog.query.order_by(AuditLog.id.desc()).limit(5000).all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "ID",
        "User",
        "Full Name",
        "Action",
        "Description",
        "IP Address",
        "Created At"
    ])

    for log in logs:
        writer.writerow([
            log.id,
            log.actor.username if log.actor else "System",
            log.actor.full_name if log.actor else "System",
            log.action or "",
            log.description or "",
            log.ip_address or "",
            log.created_at.isoformat() if log.created_at else ""
        ])

    csv_data = output.getvalue()
    output.close()

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=audit_logs_report.csv"
        }
    )