import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "super-secret-key")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:////tmp/event_guest.db"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False