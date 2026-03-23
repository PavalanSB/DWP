import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration for the Digital Wellness Platform."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    MONGO_URI = os.environ.get(
        "MONGO_URI", "mongodb://localhost:27017/dwp"
    )

    # Application-specific settings
    REMEMBER_COOKIE_DURATION_DAYS = 7
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads", "avatars")
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2 MB

    # OAuth (set in env or .env; create apps at Google Cloud Console)
    # Base URL used for OAuth redirect_uri - must match Authorized redirect URIs in Google Cloud
    OAUTH_BASE_URL = os.environ.get("OAUTH_BASE_URL", "http://localhost:5000").rstrip("/")
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    FACEBOOK_CLIENT_ID = os.environ.get("FACEBOOK_APP_ID", "") or os.environ.get("FACEBOOK_CLIENT_ID", "")
    FACEBOOK_CLIENT_SECRET = os.environ.get("FACEBOOK_APP_SECRET", "") or os.environ.get("FACEBOOK_CLIENT_SECRET", "")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}


def get_config():
    env = os.environ.get("FLASK_ENV", "development").lower()
    return config_by_name.get(env, DevelopmentConfig)

