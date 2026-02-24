import os


def _normalize_database_url(url: str) -> str:
    if "@db:" in url and not os.path.exists("/.dockerenv"):
        return url.replace("@db:", "@localhost:")
    return url


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///boxedwithlove.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 3,     
        "max_overflow": 20,    
        "pool_timeout": 30,     
        "pool_pre_ping": True,  
    }

    # Simple pagination defaults
    DEFAULT_LIMIT = int(os.getenv("DEFAULT_LIMIT", "12"))
    MAX_LIMIT = int(os.getenv("MAX_LIMIT", "50"))