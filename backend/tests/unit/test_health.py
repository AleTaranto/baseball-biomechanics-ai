from app.main import app
from fastapi.testclient import TestClient


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_and_dashboard_endpoint() -> None:
    with TestClient(app) as client:
        root_res = client.get("/")
        assert root_res.status_code == 200
        assert "dashboard_url" in root_res.json()

        dash_res = client.get("/dashboard/")
        assert dash_res.status_code == 200
        assert "Baseball Biomechanics AI" in dash_res.text
