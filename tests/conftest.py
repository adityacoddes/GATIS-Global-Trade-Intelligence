import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture(scope="session")
def client():
    """Provides a FastAPI TestClient instance for testing."""
    with TestClient(app) as c:
        yield c
