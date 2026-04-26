import os


class Config:
    # Secret key (inachukuliwa kutoka Render environment)
    SECRET_KEY = os.environ.get("SECRET_KEY") or "super-secret-key"

    # Database configuration
    DATABASE_URL = os.environ.get("DATABASE_URL")

    if DATABASE_URL:
        # Render/PostgreSQL hutumia postgres:// badala ya postgresql://
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        # Fallback ya SQLite (Render safe)
        SQLALCHEMY_DATABASE_URI = "sqlite:////tmp/event_guest.db"

    SQLALCHEMY_TRACK_MODIFICATIONS = False