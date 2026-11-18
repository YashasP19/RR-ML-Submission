"""WSGI entry point used by gunicorn:  gunicorn webapp.wsgi:app"""
from . import create_app

app = create_app()
