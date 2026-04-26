# app/models.py

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    full_name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    role = db.Column(db.String(50), default="User", nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    can_manage_guests = db.Column(db.Boolean, default=False, nullable=False)
    can_checkin = db.Column(db.Boolean, default=False, nullable=False)
    can_manage_users = db.Column(db.Boolean, default=False, nullable=False)
    can_access_admin = db.Column(db.Boolean, default=False, nullable=False)
    can_view_reports = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def apply_role_defaults(self):
        if self.role == "Admin":
            self.can_manage_guests = True
            self.can_checkin = True
            self.can_manage_users = True
            self.can_access_admin = True
            self.can_view_reports = True

    def permissions_dict(self):
        return {
            "can_manage_guests": self.can_manage_guests,
            "can_checkin": self.can_checkin,
            "can_manage_users": self.can_manage_users,
            "can_access_admin": self.can_access_admin,
            "can_view_reports": self.can_view_reports
        }

    def to_dict(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "permissions": self.permissions_dict(),
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Guest(db.Model):
    __tablename__ = "guests"

    id = db.Column(db.Integer, primary_key=True)

    full_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(30), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    organization = db.Column(db.String(150), nullable=True)
    title = db.Column(db.String(150), nullable=True)

    code_no = db.Column(db.String(50), unique=True, nullable=False, index=True)
    status = db.Column(db.String(30), default="Pending", nullable=False)

    checked_in_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "phone": self.phone,
            "email": self.email,
            "organization": self.organization,
            "title": self.title,
            "code_no": self.code_no,
            "status": self.status,
            "checked_in_at": self.checked_in_at.isoformat() if self.checked_in_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)

    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    actor = db.relationship("User", backref="audit_logs")

    def to_dict(self):
        return {
            "id": self.id,
            "actor_user_id": self.actor_user_id,
            "username": self.actor.username if self.actor else "System",
            "full_name": self.actor.full_name if self.actor else "System",
            "action": self.action,
            "description": self.description,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class TokenBlocklist(db.Model):
    __tablename__ = "token_blocklist"

    id = db.Column(db.Integer, primary_key=True)

    jti = db.Column(db.String(255), nullable=False, unique=True, index=True)
    token_type = db.Column(db.String(50), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class CheckinSettings(db.Model):
    __tablename__ = "checkin_settings"

    id = db.Column(db.Integer, primary_key=True)

    manual_lock = db.Column(db.Boolean, default=False, nullable=False)
    manual_lock_until = db.Column(db.DateTime, nullable=True)
    event_end_time = db.Column(db.DateTime, nullable=True)

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    def is_auto_locked(self):
        if not self.event_end_time:
            return False
        return datetime.utcnow() >= self.event_end_time

    def is_manually_locked(self):
        if not self.manual_lock:
            return False

        if self.manual_lock_until and datetime.utcnow() > self.manual_lock_until:
            return False

        return True

    def is_checkin_locked(self):
        return self.is_manually_locked() or self.is_auto_locked()

    def lock_reason(self):
        if self.is_manually_locked():
            return "manual"

        if self.is_auto_locked():
            return "event_ended"

        return None

    def to_dict(self):
        return {
            "manual_lock": self.manual_lock,
            "manual_lock_until": self.manual_lock_until.isoformat() if self.manual_lock_until else None,
            "event_end_time": self.event_end_time.isoformat() if self.event_end_time else None,
            "is_locked": self.is_checkin_locked(),
            "lock_reason": self.lock_reason(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class EventSettings(db.Model):
    __tablename__ = "event_settings"

    id = db.Column(db.Integer, primary_key=True)

    event_name = db.Column(db.String(255), default="Nexa Event Pro", nullable=False)
    client_name = db.Column(db.String(255), nullable=True)
    event_date = db.Column(db.String(100), nullable=True)
    venue = db.Column(db.String(255), nullable=True)
    logo_url = db.Column(db.String(255), nullable=True)

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    def to_dict(self):
        return {
            "id": self.id,
            "event_name": self.event_name,
            "client_name": self.client_name,
            "event_date": self.event_date,
            "venue": self.venue,
            "logo_url": self.logo_url,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }