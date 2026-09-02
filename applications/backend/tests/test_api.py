from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "service": "finops-api",
        "status": "running",
    }


def test_version():
    response = client.get("/version")

    assert response.status_code == 200
    assert response.json() == {
        "version": "auto-cd-test",
    }

def test_liveness():
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {
        "status": "alive",
    }
