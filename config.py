import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuración centralizada de la aplicación Flask."""

    # ── Flask ──────────────────────────────────────────
    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    PORT = int(os.getenv("FLASK_PORT", 5000))
    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default-secret-change-me")

    # ── JWT ────────────────────────────────────────────
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default-secret-change-me")
    JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", 24))

    # ── Google Sheets ──────────────────────────────────
    GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "")
    GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
    USERS_SHEET_NAME = os.getenv("USERS_SHEET_NAME", "usuarios")
    CERTIFICATES_SHEET_NAME = os.getenv("CERTIFICATES_SHEET_NAME", "certificados")

    # ── Email ──────────────────────────────────────────
    EMAIL_SENDER = os.getenv("EMAIL_SENDER", "")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
    EMAIL_SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")
    EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", 587))

    # ── Archivos ───────────────────────────────────────
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "certs")
    ALLOWED_EXTENSIONS = {"pdf"}