import os

# These must be set before importing app.py, because app.py reads them at module load time.
os.environ.setdefault("FLASK_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test_db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")

import pytest
from app import app as flask_app, limiter


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    # Flask-Limiter caches `enabled` at init time, so we must set the instance
    # attribute directly — changing app.config after import has no effect.
    limiter.enabled = False
    with flask_app.test_client() as c:
        yield c
    limiter.enabled = True
