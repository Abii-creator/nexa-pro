import os

# Base directory ya project
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Security key (inatoka Render Environment Variables)
    SECRET_KEY = os.environ.get("SECRET_KEY", "super-secret-key")

    # Database (Render-friendly path)
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:////tmp/event_guest.db"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False