# BUILDER
FROM python:3.14.4-alpine3.23 AS builder

WORKDIR /app
RUN apk add --no-cache gcc musl-dev mysql-dev pkgconfig && \
    python -m venv /app/env && \
    /app/env/bin/pip install --upgrade pip
COPY requirements.txt .

RUN /app/env/bin/pip install --no-cache-dir -r requirements.txt

# SERVER
FROM python:3.14.4-alpine3.23

ENV APP_HOST=0.0.0.0 \
    PATH="/app/env/bin:$PATH"
WORKDIR /app

RUN apk update && \
    apk upgrade --no-cache && \
    apk add --no-cache curl mariadb-connector-c && \
    python -m pip install --upgrade pip
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

COPY --from=builder /app/env /app/env
COPY src/ .

RUN chown -R appuser:appgroup /app
USER appuser

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -fsS --max-time 2 http://localhost:8000/health || exit 1
ENTRYPOINT ["sh", "-c", "exec gunicorn --bind ${APP_HOST}:8000 --config /app/gunicorn.conf.py api.wsgi:application"]
