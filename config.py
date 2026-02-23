import os


def _normalize_database_url(url: str) -> str:
    # Docker service DNS name `db` is only resolvable from inside containers.
    # When running Flask from host (PowerShell), transparently map it to localhost.
    if "@db:" in url and not os.path.exists("/.dockerenv"):
        return url.replace("@db:", "@localhost:")
    return url


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///boxedwithlove.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Simple pagination defaults
    DEFAULT_LIMIT = int(os.getenv("DEFAULT_LIMIT", "12"))
    MAX_LIMIT = int(os.getenv("MAX_LIMIT", "50"))
