"""FastAPI entrypoint. Run with: uvicorn main:app --port 8000 (from apps/api/)."""

from verine.api.app import create_app

app = create_app()
