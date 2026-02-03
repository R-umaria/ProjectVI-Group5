"""WSGI entrypoint used by Gunicorn."""
from boxedwithlove.app.factory import create_app

app = create_app()
