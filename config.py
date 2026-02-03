import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///boxedwithlove.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Simple pagination defaults
    DEFAULT_LIMIT = int(os.getenv("DEFAULT_LIMIT", "12"))
    MAX_LIMIT = int(os.getenv("MAX_LIMIT", "50"))
