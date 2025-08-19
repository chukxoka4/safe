
import pytest
from app import FlaskApp

def test_home_route():
    app = FlaskApp().app
    with app.test_client() as client:
        response = client.get('/')
        assert response.status_code == 200
        assert b"AI-Enhanced Revision System" in response.data
