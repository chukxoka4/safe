import pytest
from app import FlaskApp
from flask import jsonify

def test_invalid_file_upload():
    app = FlaskApp().app
    with app.test_client() as client:
        data = {
            'file': (open("tests/sample_files/sample.txt", "rb"), "sample.txt")
        }
        response = client.post('/upload', data=data, content_type='multipart/form-data')
        assert response.status_code == 400

def test_api_failure(monkeypatch):
    app = FlaskApp().app

    # Mock get_embedding to raise an exception
    monkeypatch.setattr("routes.main_routes.MainRoutes.get_embedding", lambda self, q: (_ for _ in ()).throw(Exception("API Error")))

    with app.test_client() as client:
        resp = client.post('/ask', json={'question': 'Test'})
        assert resp.status_code == 500
        assert b"API Error" in resp.data
