FROM mcr.microsoft.com/playwright/python:v1.64.1-noble
# checkov:skip=CKV_DOCKER_2:One-shot browser runner exits with the pytest result.
# checkov:skip=CKV_DOCKER_3:Official Playwright root setup runs only trusted isolated test applications and writes bind-mounted reports.
WORKDIR /tests
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["pytest", "-q", "--browser=chromium", "--tracing=retain-on-failure", "--screenshot=only-on-failure", "--output=/reports/artifacts", "--junitxml=/reports/browser.xml"]
