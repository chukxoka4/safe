import os

TEST_DIRS = [
    "tests",
    "tests/unit",
    "tests/integration",
    "tests/fixtures",
    "tests/security",
    "tests/sample_files"
]

TEST_FILES = {
    "tests/unit/test_file_validation.py": '''
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
''',

    "tests/unit/test_core_functions.py": '''
import pytest
from app import FlaskApp

def test_home_route():
    app = FlaskApp().app
    with app.test_client() as client:
        response = client.get('/')
        assert response.status_code == 200
        assert b"AI-Enhanced Revision System" in response.data
''',

    "tests/integration/test_upload_and_qa.py": '''
import pytest
from app import FlaskApp

def test_full_upload_and_qa_workflow(monkeypatch):
    app = FlaskApp().app
    with app.test_client() as client:
        # Upload PDF
        data = {
            'file': (open("tests/sample_files/sample.pdf", "rb"), "sample.pdf")
        }
        upload_resp = client.post('/upload', data=data, content_type='multipart/form-data')
        assert upload_resp.status_code == 200

        # Ask a question
        qa_resp = client.post('/ask', data={'question': 'What is AI?'})
        assert qa_resp.status_code == 200
        assert b"answer" in qa_resp.data
''',

    "tests/integration/test_error_handling.py": '''
import pytest
from app import FlaskApp

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

    def mock_ask(*args, **kwargs):
        return ("API Error", 500)

    monkeypatch.setattr("routes.main_routes.MainRoutes.ask", mock_ask)
    with app.test_client() as client:
        resp = client.post('/ask', data={'question': 'Test'})
        assert resp.status_code == 500
''',

    "tests/fixtures/conftest.py": '''
import pytest

@pytest.fixture
def sample_pdf_path():
    return "tests/sample_files/sample.pdf"

@pytest.fixture
def sample_txt_path():
    return "tests/sample_files/sample.txt"
''',

    "tests/sample_files/sample.pdf": "%PDF-1.4\n%Fake PDF for testing\n1 0 obj\n<< /Type /Catalog >>\nendobj\n",
    "tests/sample_files/sample.txt": "This is a plain text file for invalid upload testing.",

    "tests/security/test_security.sh": '''
#!/bin/bash
echo "Running basic security checks..."
bandit -r ../../app.py
''',

    "tests/security/test_deploy.sh": '''
#!/bin/bash
echo "Simulating deployment..."
pytest ../unit
pytest ../integration
''',

    "locustfile.py": '''
from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    wait_time = between(1, 5)

    @task
    def upload_pdf(self):
        with open("tests/sample_files/sample.pdf", "rb") as f:
            self.client.post("/upload", files={"file": ("sample.pdf", f, "application/pdf")})

    @task
    def ask_question(self):
        self.client.post("/ask", data={"question": "What is AI?"})
'''
}

def create_dirs_and_files():
    for d in TEST_DIRS:
        os.makedirs(d, exist_ok=True)
    for path, content in TEST_FILES.items():
        with open(path, "w") as f:
            f.write(content)

if __name__ == "__main__":
    create_dirs_and_files()
    print("Test directories and files created.")