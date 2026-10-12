"""Entrypoint:  uvicorn main:app --port 8000   (API docs at /docs)"""
from whybot.api.app import create_app

app = create_app()
