from fastapi.testclient import TestClient
from main import app

from .db import SessionLocal


client = TestClient(app)


def get_db():
    session = SessionLocal()
    try:
        yield session
    except:
        session.close()


app.dependency_overrides['get_db'] = get_db


def test_home_renders_models_list():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert 'Color' in response.text
    assert 'Flower' in response.text
