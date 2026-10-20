FROM mysql:26.7.0-oraclelinux9

RUN microdnf upgrade -y && \
    microdnf clean all

COPY ./data.sql /docker-entrypoint-initdb.d/

