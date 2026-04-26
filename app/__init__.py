# app/__init__.py

from flask import Flask
from .config import Config
from .extensions import db, migrate, jwt, cors

from .routes.auth import auth_bp
from .routes.users import users_bp
from .routes.guests import guests_bp
from .routes.checkin import checkin_bp
from .routes.admin import admin_bp
from .routes.reports import reports_bp

from .web import web_bp

from .models import User, TokenBlocklist, CheckinSettings, EventSettings


def create_app():
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static"
    )

    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app)

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(users_bp, url_prefix="/api/users")
    app.register_blueprint(guests_bp, url_prefix="/api/guests")
    app.register_blueprint(checkin_bp, url_prefix="/api/checkin")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(reports_bp, url_prefix="/api/reports")

    app.register_blueprint(web_bp)

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload["jti"]
        token = TokenBlocklist.query.filter_by(jti=jti).first()
        return token is not None

    @app.after_request
    def add_no_cache_headers(response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0, private"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    with app.app_context():
        db.create_all()

        admin = User.query.filter_by(username="admin").first()

        if not admin:
            admin = User(
                full_name="System Administrator",
                username="admin",
                email="admin@nexa.local",
                role="Admin",
                is_active=True,
                can_manage_guests=True,
                can_checkin=True,
                can_manage_users=True,
                can_access_admin=True,
                can_view_reports=True
            )
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()
            print("Default admin created: admin / admin123")

        else:
            admin.full_name = "System Administrator"
            admin.email = "admin@nexa.local"
            admin.role = "Admin"
            admin.is_active = True
            admin.can_manage_guests = True
            admin.can_checkin = True
            admin.can_manage_users = True
            admin.can_access_admin = True
            admin.can_view_reports = True
            db.session.commit()
            print("Default admin checked and updated")

        checkin_settings = CheckinSettings.query.first()

        if not checkin_settings:
            checkin_settings = CheckinSettings(
                manual_lock=False,
                manual_lock_until=None,
                event_end_time=None
            )
            db.session.add(checkin_settings)
            db.session.commit()
            print("Default check-in settings created")

        event_settings = EventSettings.query.first()

        if not event_settings:
            event_settings = EventSettings(
                event_name="Nexa Event Pro",
                client_name="Default Client",
                event_date="",
                venue="",
                logo_url=""
            )
            db.session.add(event_settings)
            db.session.commit()
            print("Default event settings created")

    return app