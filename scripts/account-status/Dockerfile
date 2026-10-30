FROM python:3.14.4-alpine3.23
WORKDIR /initializer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    addgroup -S initializer && adduser -S initializer -G initializer
COPY initialize.py .
USER initializer
# checkov:skip=CKV_DOCKER_2:One-shot initialization exits after provisioning status.
ENTRYPOINT ["python", "initialize.py"]
