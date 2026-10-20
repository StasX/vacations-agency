FROM mysql:26.7.0

RUN dnf upgrade -y \
        --exclude='mysql*' \
        --exclude='mysql-community-*' && \
    dnf clean all

COPY ./data.sql /docker-entrypoint-initdb.d

USER mysql
