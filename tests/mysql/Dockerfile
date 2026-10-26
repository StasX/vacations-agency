FROM python:3.14.4-alpine3.23

RUN apk add --no-cache gcc musl-dev mysql-dev pkgconfig
RUN addgroup -S testgroup && adduser -S testuser -G testgroup
ARG APPLICATION
COPY Django/requirements*.txt /requirements/Django/
COPY Flask/requirements*.txt /requirements/Flask/
RUN python -m pip install --no-cache-dir -r /requirements/${APPLICATION}/requirements-dev.txt

WORKDIR /app
COPY Django/src /app/Django/src
COPY Flask/src /app/Flask/src
COPY tests/mysql /app/tests/mysql
COPY tests/redis /app/tests/redis
USER testuser:testgroup
# checkov:skip=CKV_DOCKER_2:One-shot test runner exits with the pytest result.
ENTRYPOINT ["python", "-m", "pytest", "-c", "tests/mysql/pytest.ini", "-p", "no:django", "-v"]
