import os

# Root paths
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
INSTANCE_DIR = os.path.join(PROJECT_DIR, "instance")

# Hakikisha instance folder ipo
os.makedirs(INSTANCE_DIR, exist_ok=True)


class Config:
    # Security
    SECRET_KEY = os.environ.get("SECRET_KEY", "amisda_secret_2026")

    # Database
    DATABASE_URL = os.environ.get("DATABASE_URL")

    if DATABASE_URL:
        # Fix kwa Render/Postgres (wanatumia postgres:// badala ya postgresql://)
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        # Local SQLite database
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(
            INSTANCE_DIR,
            "event_guest.db"
        ).replace("\\", "/")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Optional (performance tuning)
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }