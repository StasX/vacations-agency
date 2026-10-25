FROM mysql:26.7.0-oraclelinux9

RUN microdnf upgrade -y && \
    microdnf clean all

COPY ./data.sql /docker-entrypoint-initdb.d/

HEALTHCHECK --interval=30s --timeout=5s \
    --start-period=60s --retries=3 \
    CMD mysqladmin ping -h 127.0.0.1 --silent || exit 1

USER mysql
