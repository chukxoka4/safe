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

        # Ask a relevant question
        qa_resp = client.post('/ask', json={'question': 'What is AI?'})
        assert qa_resp.status_code == 200
        assert b"AI" in qa_resp.data or b"artificial intelligence" in qa_resp.data

        # Ask an irrelevant question
        qa_resp = client.post('/ask', json={'question': 'What is the capital of France?'})
        assert b"cannot answer" in qa_resp.data or qa_resp.status_code == 200
