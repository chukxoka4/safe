# Safe-AI

Minimal instructions to set up, run, test, and safely publish this Flask project.

## Repository layout (key files)
- `app.py` — application entry (FlaskApp)  
- `routes/main_routes.py` — upload / ask logic  
- `requirements.txt` — Python dependencies  
- `tests/` — unit, integration, security, performance tests  
- `tests/performance/` — Locust load tests  
- `uploads/`, `*.pkl`, `*.index` — runtime/generated files (excluded)

## Prerequisites
- Python 3.10+  
- Git  
- Recommended: virtual environment

## Quick local setup
1. Clone the repo:
   git clone <your-repo-url>
   cd <repo-dir>

2. Create & activate a virtual environment:
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell)

3. Install dependencies:
   pip install -r requirements.txt

4. Create local environment variables:
   - Copy `.env.example` → `.env` and fill values
   - Do NOT commit `.env`

5. Run the app (development):
   source .venv/bin/activate   # if not already activated
   python app.py
   Then open http://127.0.0.1:5000 in your browser.

   Alternatively: export FLASK_APP=app.py && flask run

## Running tests
- Unit/integration:
  pytest tests/unit tests/integration
- Security checks:
  see `tests/security/`
- Performance (Locust):
  see `tests/performance/` (example headless command below)

## Performance testing (example)
Generate large PDFs if needed:
python tests/performance/generate_large_pdf.py

Run Locust headless:
locust -f tests/performance/locust_suite.py --headless -u 20 -r 5 --run-time 2m --host=http://localhost:5000 --html tests/performance/report_20_users.html

## Files excluded from the public repo (and why)
These are listed in `.gitignore` and should NOT be committed:

- `.env` — API keys and secrets. Never commit.
- `uploads/` — user-uploaded data (PII / private).
- `*.pkl`, `*.index` (e.g., `id_to_text.pkl`, `faiss_index.index`) — binary/model/index files; large and potentially sensitive.
- `tests/performance/report_*.html` — generated artifacts.
- `__pycache__/`, `.pytest_cache/`, `*.pyc`, `*.log`, `.DS_Store`, `.vscode/` — local/IDE artifacts.

## If sensitive files were accidentally committed
1. Remove the file from the index (keeps local copy):
   git rm --cached path/to/file
   git commit -m "Remove sensitive file"

2. Add to `.gitignore` and commit.

3. To purge from history (use with caution):
   - Use `git filter-repo` or BFG (recommended).
   - Example (git filter-repo):  
     git filter-repo --path faiss_index.index --invert-paths

4. After rewriting history, force-push:
   git push --force origin main  
   Note: force-push rewrites history and affects collaborators. Rotate any exposed secrets immediately.

## Creating `requirements.txt`
- Capture exact installed versions:
  pip freeze > requirements.txt

## Safety checklist before publishing
- Confirm `.gitignore` contains `.env`, `uploads/`, `*.pkl`, `*.index`, and other local artifacts.
- Run:
  git ls-files | grep -E '\.env|\.pkl|\.index|uploads/|tests/performance/report_' || echo "No tracked sensitive files found"
- If any sensitive files are tracked, remove and remediate as above.

## Contact / contribution
Open issues or pull requests for improvements.
