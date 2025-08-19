
import pytest
from werkzeug.datastructures import FileStorage
from app import FlaskApp

def test_valid_pdf_file():
    app = FlaskApp().app
    with app.test_client() as client:
        data = {
            'file': (open("tests/sample_files/sample.pdf", "rb"), "sample.pdf")
        }
        response = client.post('/upload', data=data, content_type='multipart/form-data')
        assert response.status_code == 200

def test_invalid_file_type():
    app = FlaskApp().app
    with app.test_client() as client:
        data = {
            'file': (open("tests/sample_files/sample.txt", "rb"), "sample.txt")
        }
        response = client.post('/upload', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
