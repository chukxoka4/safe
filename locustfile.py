
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
