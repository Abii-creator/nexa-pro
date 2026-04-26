import os


class Config:
    # Secret key kutoka Render environment
    SECRET_KEY = os.environ.get("SECRET_KEY", "super-secret-key")

    # Database (IMPORTANT: slash 4 kwa Render)
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:////tmp/event_guest.db"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False