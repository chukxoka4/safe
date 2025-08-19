from locust import HttpUser, task, between, events
import os

PDF_PATH = "tests/sample_files/sample.pdf"
LARGE_PDF_PATH = "tests/sample_files/large_sample.pdf"

class WebsiteUser(HttpUser):
    wait_time = between(1, 2)

    @task(2)
    def upload_pdf(self):
        path = LARGE_PDF_PATH if os.path.exists(LARGE_PDF_PATH) else PDF_PATH
        with open(path, "rb") as f:
            self.client.post("/upload", files={"file": ("sample.pdf", f, "application/pdf")})

    @task(3)
    def ask_question(self):
        self.client.post("/ask", json={"question": "What is AI?"})

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("Test finished. See Locust HTML report for details.")