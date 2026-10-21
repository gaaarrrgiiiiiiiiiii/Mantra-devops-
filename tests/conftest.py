import sys
from pathlib import Path

# Add backend directory to sys.path for IDE module resolution (Pyrefly/Pylance) and pytest
backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

import pytest
from fastapi.testclient import TestClient

try:
    from app.main import app
except ImportError:
    from backend.app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
