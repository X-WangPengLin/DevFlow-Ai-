from fastapi.testclient import TestClient

from devflow_rag.main import app


def test_database_health_with_real_postgres() -> None:
    response = TestClient(app).get("/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
