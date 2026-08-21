from app.main import app
from fastapi.testclient import TestClient


def client() -> TestClient:
    return TestClient(app)
