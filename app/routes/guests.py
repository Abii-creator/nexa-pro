from datetime import datetime
import os
import csv
import io
import html
from urllib.parse import quote
import qrcode

from flask import Blueprint, jsonify, request, session, send_file, current_app, Response

from app.extensions import db
from app.models import Guest, User, CheckinSettings, EventSettings
from app.audit import log_activity
from app.services.whatsapp import send_whatsapp_qr


guests_bp = Blueprint("guests", __name__)


def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)


def unauthorized():
    return jsonify({"error": "Unauthorized"}), 401


def forbidden(message="Permission denied"):
    return jsonify({"error": message}), 403


def require_admin():
    user = get_current_user()
    if not user:
        return None, unauthorized()

    if not user.is_active:
        return None, forbidden("Inactive or invalid account")

    if (user.role or "").strip().lower() != "admin":
        return None, forbidden("Admin access required")

    return user, None


def require_checkin_access():
    user = get_current_user()
    if not user:
        return None, unauthorized()

    if not user.is_active:
        return None, forbidden("Inactive or invalid account")

    role = (user.role or "").strip().lower()
    if not (role == "admin" or bool(user.can_checkin)):
        return None, forbidden("Check-in access required")

    return user, None


def get_event_settings():
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


def generate_guest_code():
    last_guest = Guest.query.order_by(Guest.id.desc()).first()
    next_id = 1 if not last_guest else last_guest.id + 1

    while True:
        code = f"GST-{next_id:05d}"
        exists = Guest.query.filter_by(code_no=code).first()
        if not exists:
            return code
        next_id += 1


def get_qr_folder():
    folder = os.path.join(current_app.root_path, "static", "qrcodes")
    os.makedirs(folder, exist_ok=True)
    return folder


def get_qr_path(code_no):
    return os.path.join(get_qr_folder(), f"{code_no}.png")


def clean_html(value):
    return html.escape(str(value or ""), quote=True)


def normalize_phone_for_whatsapp(phone):
    raw = "".join(ch for ch in (phone or "") if ch.isdigit())

    if not raw:
        return ""

    if raw.startswith("00"):
        raw = raw[2:]

    if raw.startswith("0"):
        return "255" + raw[1:]

    if raw.startswith("255"):
        return raw

    if len(raw) == 9:
        return "255" + raw

    return raw


def guest_qr_text(guest):
    event = get_event_settings()

    return (
        f"{event.event_name or 'Nexa Event Pro'}\n"
        f"Client: {event.client_name or '-'}\n"
        f"Event Date: {event.event_date or '-'}\n"
        f"Venue: {event.venue or '-'}\n"
        f"Guest Name: {guest.full_name or '-'}\n"
        f"Phone: {guest.phone or '-'}\n"
        f"Email: {guest.email or '-'}\n"
        f"Organization: {guest.organization or '-'}\n"
        f"Category: {guest.title or '-'}\n"
        f"Invitation Code: {guest.code_no or '-'}"
    )


def generate_qr_code(guest):
    qr_path = get_qr_path(guest.code_no)

    qr = qrcode.QRCode(
        version=4,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4
    )

    qr.add_data(guest_qr_text(guest))
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img.save(qr_path)

    return qr_path


def guest_dict(guest):
    data = guest.to_dict()
    data["qr_code_url"] = f"/api/guests/{guest.id}/qr"
    data["qr_card_url"] = f"/api/guests/{guest.id}/qr-card"
    data["qr_download_url"] = f"/api/guests/{guest.id}/qr/download"
    data["whatsapp_send_url"] = f"/api/guests/{guest.id}/send-whatsapp"
    return data


def send_guest_whatsapp_qr(guest, qr_path=None):
    whatsapp_phone = normalize_phone_for_whatsapp(guest.phone)

    if not whatsapp_phone:
        result = {
            "success": False,
            "error": "Guest hana phone number"
        }
        print("WHATSAPP QR SEND RESULT:", result)
        return result

    if not qr_path:
        qr_path = generate_qr_code(guest)

    result = send_whatsapp_qr(
        to_phone=whatsapp_phone,
        image_path=qr_path,
        guest_name=guest.full_name,
        guest_code=guest.code_no
    )

    print("WHATSAPP QR SEND RESULT:", result)
    return result


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


@guests_bp.get("/")
def list_guests():
    current_user, error = require_admin()
    if error:
        return error

    search = request.args.get("search", "").strip()
    query = Guest.query

    if search:
        like_term = f"%{search}%"
        query = query.filter(
            (Guest.full_name.ilike(like_term)) |
            (Guest.phone.ilike(like_term)) |
            (Guest.email.ilike(like_term)) |
            (Guest.code_no.ilike(like_term)) |
            (Guest.status.ilike(like_term)) |
            (Guest.organization.ilike(like_term)) |
            (Guest.title.ilike(like_term))
        )

    guests = query.order_by(Guest.id.desc()).all()
    return jsonify([guest_dict(guest) for guest in guests]), 200


@guests_bp.post("/")
def create_guest():
    current_user, error = require_admin()
    if error:
        return error

    try:
        data = request.get_json() or {}

        full_name = (data.get("full_name") or "").strip()
        phone = (data.get("phone") or "").strip()
        email = (data.get("email") or "").strip()
        organization = (data.get("organization") or "").strip()
        title = (data.get("title") or "").strip()

        if not full_name:
            return jsonify({"error": "Full name is required"}), 400

        guest = Guest(
            full_name=full_name,
            phone=phone or None,
            email=email or None,
            organization=organization or None,
            title=title or None,
            code_no=generate_guest_code(),
            status="Pending"
        )

        db.session.add(guest)
        db.session.commit()

        qr_path = generate_qr_code(guest)
        whatsapp_result = send_guest_whatsapp_qr(guest, qr_path)

        log_activity(
            actor_user_id=current_user.id,
            action="CREATE_GUEST",
            description=f"Created guest '{guest.full_name}' ({guest.code_no})"
        )

        return jsonify({
            "message": "Guest created successfully",
            "guest": guest_dict(guest),
            "whatsapp": whatsapp_result
        }), 201

    except Exception as e:
        db.session.rollback()
        print("CREATE GUEST ERROR:", str(e))
        return jsonify({"error": "Failed to create guest"}), 500


@guests_bp.post("/bulk-import")
def bulk_import_guests():
    current_user, error = require_admin()
    if error:
        return error

    try:
        if "file" not in request.files:
            return jsonify({"error": "CSV file is required"}), 400

        file = request.files["file"]

        if not file.filename.lower().endswith(".csv"):
            return jsonify({"error": "Only CSV files are allowed"}), 400

        raw = file.read().decode("utf-8-sig")
        stream = io.StringIO(raw)
        reader = csv.DictReader(stream)

        if not reader.fieldnames:
            return jsonify({"error": "CSV file has no header row"}), 400

        normalized_headers = [h.strip().lower() for h in reader.fieldnames]

        if "full_name" not in normalized_headers:
            return jsonify({"error": "CSV must contain full_name column"}), 400

        created = 0
        skipped = 0
        whatsapp_sent = 0
        whatsapp_failed = 0
        errors = []

        for index, row in enumerate(reader, start=2):
            clean_row = {}

            for key, value in row.items():
                clean_key = (key or "").strip().lower()
                clean_row[clean_key] = (value or "").strip()

            full_name = clean_row.get("full_name", "")
            phone = clean_row.get("phone", "")
            email = clean_row.get("email", "")
            organization = clean_row.get("organization", "")
            title = clean_row.get("title", "")

            if not full_name:
                skipped += 1
                errors.append(f"Row {index}: full_name is missing")
                continue

            guest = Guest(
                full_name=full_name,
                phone=phone or None,
                email=email or None,
                organization=organization or None,
                title=title or None,
                code_no=generate_guest_code(),
                status="Pending"
            )

            db.session.add(guest)
            db.session.commit()

            qr_path = generate_qr_code(guest)
            whatsapp_result = send_guest_whatsapp_qr(guest, qr_path)

            if whatsapp_result.get("success"):
                whatsapp_sent += 1
            else:
                whatsapp_failed += 1
                errors.append(f"Row {index}: WhatsApp failed - {whatsapp_result}")

            created += 1

        log_activity(
            actor_user_id=current_user.id,
            action="BULK_IMPORT_GUESTS",
            description=f"Bulk imported guests. Created: {created}, Skipped: {skipped}, WhatsApp Sent: {whatsapp_sent}, WhatsApp Failed: {whatsapp_failed}"
        )

        return jsonify({
            "message": "Bulk import completed",
            "created": created,
            "skipped": skipped,
            "whatsapp_sent": whatsapp_sent,
            "whatsapp_failed": whatsapp_failed,
            "errors": errors[:50]
        }), 200

    except UnicodeDecodeError:
        return jsonify({"error": "Invalid file encoding. Save CSV as UTF-8."}), 400

    except Exception as e:
        db.session.rollback()
        print("BULK IMPORT ERROR:", str(e))
        return jsonify({"error": "Failed to import guests"}), 500


@guests_bp.post("/<int:guest_id>/send-whatsapp")
def resend_guest_whatsapp(guest_id):
    current_user, error = require_admin()
    if error:
        return error

    try:
        guest = Guest.query.get(guest_id)

        if not guest:
            return jsonify({"error": "Guest not found"}), 404

        qr_path = generate_qr_code(guest)
        whatsapp_result = send_guest_whatsapp_qr(guest, qr_path)

        log_activity(
            actor_user_id=current_user.id,
            action="SEND_GUEST_WHATSAPP",
            description=f"Sent WhatsApp QR to '{guest.full_name}' ({guest.code_no})"
        )

        return jsonify({
            "message": "WhatsApp send processed",
            "guest": guest_dict(guest),
            "whatsapp": whatsapp_result
        }), 200

    except Exception as e:
        print("SEND WHATSAPP ERROR:", str(e))
        return jsonify({"error": "Failed to send WhatsApp QR"}), 500


@guests_bp.get("/print-badges")
def print_guest_badges():
    current_user, error = require_admin()
    if error:
        return error

    event = get_event_settings()

    search = request.args.get("search", "").strip()
    query = Guest.query

    if search:
        like_term = f"%{search}%"
        query = query.filter(
            (Guest.full_name.ilike(like_term)) |
            (Guest.phone.ilike(like_term)) |
            (Guest.email.ilike(like_term)) |
            (Guest.code_no.ilike(like_term)) |
            (Guest.organization.ilike(like_term)) |
            (Guest.title.ilike(like_term)) |
            (Guest.status.ilike(like_term))
        )

    guests = query.order_by(Guest.id.asc()).all()

    for guest in guests:
        generate_qr_code(guest)

    cards = ""

    for guest in guests:
        cards += f"""
        <div class="badge-card">
            <div class="event-name">{clean_html(event.event_name or 'Nexa Event Pro')}</div>
            <div class="client-name">{clean_html(event.client_name or '')}</div>
            <h3>{clean_html(guest.full_name or '-')}</h3>
            <p>{clean_html(guest.organization or '-')}</p>
            <img src="/api/guests/{guest.id}/qr" alt="QR Code">
            <strong>{clean_html(guest.code_no)}</strong>
            <small>{clean_html(guest.phone or '')}</small>
        </div>
        """

    html_page = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Print QR Badges</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: #f4f4f4;
                margin: 0;
                padding: 20px;
            }}
            .top-actions {{
                margin-bottom: 20px;
                text-align: center;
            }}
            button {{
                padding: 10px 18px;
                border: none;
                border-radius: 8px;
                background: #3867f3;
                color: white;
                font-weight: bold;
                cursor: pointer;
            }}
            .grid {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 14px;
            }}
            .badge-card {{
                background: white;
                border: 1px solid #222;
                border-radius: 10px;
                padding: 12px;
                text-align: center;
                min-height: 285px;
                page-break-inside: avoid;
            }}
            .event-name {{
                font-size: 13px;
                font-weight: bold;
                color: #111;
                margin-bottom: 3px;
            }}
            .client-name {{
                font-size: 11px;
                color: #333;
                margin-bottom: 8px;
            }}
            .badge-card h3 {{
                margin: 0 0 6px;
                font-size: 16px;
                color: #111;
            }}
            .badge-card p {{
                margin: 0 0 10px;
                font-size: 12px;
                color: #444;
            }}
            .badge-card img {{
                width: 130px;
                height: 130px;
                margin: 6px auto;
                display: block;
            }}
            .badge-card strong {{
                display: block;
                margin-top: 8px;
                font-size: 14px;
                color: #111;
            }}
            .badge-card small {{
                display: block;
                margin-top: 4px;
                color: #555;
            }}
            @media print {{
                body {{
                    background: white;
                    padding: 0;
                }}
                .top-actions {{
                    display: none;
                }}
                .grid {{
                    gap: 8px;
                }}
                .badge-card {{
                    box-shadow: none;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="top-actions">
            <button onclick="window.print()">Print Badges</button>
        </div>

        <div class="grid">
            {cards}
        </div>
    </body>
    </html>
    """

    return Response(html_page, mimetype="text/html")


@guests_bp.get("/<int:guest_id>")
def get_guest(guest_id):
    current_user, error = require_admin()
    if error:
        return error

    guest = Guest.query.get(guest_id)

    if not guest:
        return jsonify({"error": "Guest not found"}), 404

    return jsonify(guest_dict(guest)), 200


@guests_bp.get("/<int:guest_id>/qr")
def get_guest_qr(guest_id):
    current_user, error = require_admin()
    if error:
        return error

    guest = Guest.query.get(guest_id)

    if not guest:
        return jsonify({"error": "Guest not found"}), 404

    generate_qr_code(guest)
    qr_path = get_qr_path(guest.code_no)

    return send_file(
        qr_path,
        mimetype="image/png",
        as_attachment=False,
        download_name=f"{guest.code_no}.png"
    )


@guests_bp.get("/<int:guest_id>/qr/download")
def download_guest_qr(guest_id):
    current_user, error = require_admin()
    if error:
        return error

    guest = Guest.query.get(guest_id)

    if not guest:
        return jsonify({"error": "Guest not found"}), 404

    generate_qr_code(guest)
    qr_path = get_qr_path(guest.code_no)

    safe_name = "".join(ch if ch.isalnum() else "_" for ch in (guest.full_name or "guest"))
    filename = f"{guest.code_no}_{safe_name}.png"

    return send_file(
        qr_path,
        mimetype="image/png",
        as_attachment=True,
        download_name=filename
    )


@guests_bp.get("/<int:guest_id>/qr-card")
def qr_card_page(guest_id):
    current_user, error = require_admin()
    if error:
        return error

    event = get_event_settings()
    guest = Guest.query.get(guest_id)

    if not guest:
        return Response("Guest not found", status=404)

    generate_qr_code(guest)

    whatsapp_phone = normalize_phone_for_whatsapp(guest.phone)

    event_name = event.event_name or "Nexa Event Pro"
    client_name = event.client_name or ""
    event_date = event.event_date or ""
    venue = event.venue or ""

    whatsapp_message = (
        f"{event_name}\n"
        f"{client_name}\n"
        f"Invitation Details\n"
        f"Name: {guest.full_name}\n"
        f"Code: {guest.code_no}\n"
        f"Date: {event_date}\n"
        f"Venue: {venue}\n"
        f"Please present this QR code at check-in."
    )

    whatsapp_link = f"https://wa.me/{whatsapp_phone}?text={quote(whatsapp_message)}" if whatsapp_phone else "#"

    email_subject = quote(f"{event_name} Invitation - {guest.code_no}")
    email_body = quote(
        f"Dear {guest.full_name},\n\n"
        f"You are invited to {event_name}.\n"
        f"Client: {client_name}\n"
        f"Date: {event_date}\n"
        f"Venue: {venue}\n"
        f"Your invitation code is {guest.code_no}.\n"
        f"Please present the QR code at check-in.\n\n"
        f"Thank you."
    )

    email_link = f"mailto:{guest.email or ''}?subject={email_subject}&body={email_body}" if guest.email else "#"

    logo_html = ""
    if event.logo_url:
        logo_html = f'<img class="logo" src="{clean_html(event.logo_url)}" alt="Event Logo">'

    html_page = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{clean_html(guest.code_no)} QR Card</title>
        <style>
            body {{
                margin: 0;
                font-family: Arial, sans-serif;
                background: #06132d;
                color: #ffffff;
                display: flex;
                justify-content: center;
                padding: 40px 16px;
            }}
            .card {{
                width: 440px;
                background: #162e67;
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 18px;
                padding: 24px;
                text-align: center;
                box-shadow: 0 16px 40px rgba(0,0,0,0.35);
            }}
            .logo {{
                max-width: 90px;
                max-height: 90px;
                object-fit: contain;
                margin-bottom: 10px;
                border-radius: 8px;
                background: #fff;
                padding: 6px;
            }}
            h1 {{
                margin: 0 0 6px;
                font-size: 24px;
            }}
            .client {{
                color: #dbe5ff;
                margin-bottom: 4px;
                font-weight: bold;
            }}
            .muted {{
                color: #c8d5ff;
                margin-bottom: 12px;
            }}
            .event-meta {{
                background: rgba(255,255,255,0.07);
                padding: 10px;
                border-radius: 12px;
                margin: 12px 0;
                line-height: 1.5;
                color: #e8eeff;
            }}
            .qr-img {{
                width: 260px;
                height: 260px;
                background: #ffffff;
                padding: 12px;
                border-radius: 12px;
                margin: 14px auto;
                display: block;
            }}
            .info {{
                text-align: left;
                margin: 18px 0;
                background: rgba(255,255,255,0.07);
                padding: 14px;
                border-radius: 12px;
                line-height: 1.7;
            }}
            .buttons {{
                display: grid;
                gap: 10px;
                margin-top: 18px;
            }}
            a, button {{
                border: none;
                border-radius: 10px;
                padding: 11px 14px;
                color: #fff;
                text-decoration: none;
                font-weight: 700;
                cursor: pointer;
            }}
            .download {{ background: #3867f3; }}
            .whatsapp {{ background: #25d366; color: #073b18; }}
            .email {{ background: #8b56f3; }}
            .print {{ background: #ff6b5c; width: 100%; }}
            @media print {{
                body {{ background: white; color: black; }}
                .card {{ box-shadow: none; border: 1px solid #222; background: white; color: black; }}
                .buttons {{ display: none; }}
                .muted, .client, .event-meta {{ color: #333; }}
                .info {{ background: #f2f2f2; }}
            }}
        </style>
    </head>
    <body>
        <div class="card">
            {logo_html}
            <h1>{clean_html(event_name)}</h1>
            <div class="client">{clean_html(client_name)}</div>
            <div class="muted">Guest QR Invitation</div>

            <div class="event-meta">
                <strong>Date:</strong> {clean_html(event_date or '-')}<br>
                <strong>Venue:</strong> {clean_html(venue or '-')}
            </div>

            <img class="qr-img" src="/api/guests/{guest.id}/qr" alt="QR Code">

            <div class="info">
                <strong>Name:</strong> {clean_html(guest.full_name or '-')}<br>
                <strong>Phone:</strong> {clean_html(guest.phone or '-')}<br>
                <strong>Email:</strong> {clean_html(guest.email or '-')}<br>
                <strong>Organization:</strong> {clean_html(guest.organization or '-')}<br>
                <strong>Category:</strong> {clean_html(guest.title or '-')}<br>
                <strong>Code:</strong> {clean_html(guest.code_no or '-')}
            </div>

            <div class="buttons">
                <a class="download" href="/api/guests/{guest.id}/qr/download">Download QR</a>
                <a class="whatsapp" href="{whatsapp_link}" target="_blank">Send via WhatsApp</a>
                <a class="email" href="{email_link}">Send via Email</a>
                <button class="print" onclick="window.print()">Print QR Card</button>
            </div>
        </div>
    </body>
    </html>
    """

    return Response(html_page, mimetype="text/html")


@guests_bp.put("/<int:guest_id>")
def update_guest(guest_id):
    current_user, error = require_admin()
    if error:
        return error

    try:
        guest = Guest.query.get(guest_id)

        if not guest:
            return jsonify({"error": "Guest not found"}), 404

        data = request.get_json() or {}

        full_name = data.get("full_name") if data.get("full_name") is not None else guest.full_name
        full_name = full_name.strip() if isinstance(full_name, str) else ""

        if not full_name:
            return jsonify({"error": "Full name is required"}), 400

        guest.full_name = full_name
        guest.phone = (data.get("phone") if data.get("phone") is not None else (guest.phone or "")).strip() or None
        guest.email = (data.get("email") if data.get("email") is not None else (guest.email or "")).strip() or None
        guest.organization = (data.get("organization") if data.get("organization") is not None else (guest.organization or "")).strip() or None
        guest.title = (data.get("title") if data.get("title") is not None else (guest.title or "")).strip() or None

        db.session.commit()
        generate_qr_code(guest)

        log_activity(
            actor_user_id=current_user.id,
            action="UPDATE_GUEST",
            description=f"Updated guest '{guest.full_name}' ({guest.code_no})"
        )

        return jsonify({
            "message": "Guest updated successfully",
            "guest": guest_dict(guest)
        }), 200

    except Exception as e:
        db.session.rollback()
        print("UPDATE GUEST ERROR:", str(e))
        return jsonify({"error": "Failed to update guest"}), 500


@guests_bp.delete("/<int:guest_id>")
def delete_guest(guest_id):
    current_user, error = require_admin()
    if error:
        return error

    try:
        guest = Guest.query.get(guest_id)

        if not guest:
            return jsonify({"error": "Guest not found"}), 404

        guest_name = guest.full_name
        guest_code = guest.code_no
        qr_path = get_qr_path(guest.code_no)

        db.session.delete(guest)
        db.session.commit()

        if os.path.exists(qr_path):
            os.remove(qr_path)

        log_activity(
            actor_user_id=current_user.id,
            action="DELETE_GUEST",
            description=f"Deleted guest '{guest_name}' ({guest_code})"
        )

        return jsonify({"message": "Guest deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        print("DELETE GUEST ERROR:", str(e))
        return jsonify({"error": "Failed to delete guest"}), 500


@guests_bp.post("/<int:guest_id>/check-in")
def check_in_guest(guest_id):
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
                description=f"Check-in blocked for guest ID {guest_id}. Reason: {reason}"
            )

            if reason == "manual":
                return jsonify({"error": "Check-in is manually locked"}), 403

            if reason == "event_ended":
                return jsonify({"error": "Check-in is closed because the event has ended"}), 403

            return jsonify({"error": "Check-in is locked"}), 403

        guest = Guest.query.get(guest_id)

        if not guest:
            return jsonify({"error": "Guest not found"}), 404

        if guest.status == "Checked-in":
            log_activity(
                actor_user_id=current_user.id,
                action="CHECK_IN_DUPLICATE",
                description=f"Duplicate check-in attempt for '{guest.full_name}' ({guest.code_no})"
            )
            return jsonify({"error": "Guest already checked in"}), 400

        guest.status = "Checked-in"
        guest.checked_in_at = datetime.utcnow()

        db.session.commit()

        log_activity(
            actor_user_id=current_user.id,
            action="CHECK_IN_GUEST",
            description=f"Checked in guest '{guest.full_name}' ({guest.code_no})"
        )

        return jsonify({
            "message": "Guest checked in successfully",
            "guest": guest_dict(guest)
        }), 200

    except Exception as e:
        db.session.rollback()
        print("CHECK-IN GUEST ERROR:", str(e))
        return jsonify({"error": "Failed to check in guest"}), 500