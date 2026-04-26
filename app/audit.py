from flask import request
from app.extensions import db
from app.models import AuditLog


def get_client_ip():
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "127.0.0.1"


def log_activity(actor_user_id=None, action="UNKNOWN", description=None):
    try:
        log = AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            description=description,
            ip_address=get_client_ip()
        )
        db.session.add(log)
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print("AUDIT LOG ERROR:", str(e))
        return False