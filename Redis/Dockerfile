FROM redis:8.2-alpine@sha256:d1389b3f3f981460b9b0918c4d7390c6e9decb8c69b9f09a02e1b6fd7554ade7

RUN apk upgrade --no-cache

COPY redis.conf /usr/local/etc/redis/redis.conf
COPY entrypoint.sh /usr/local/bin/redis-hardened-entrypoint
RUN chmod 0444 /usr/local/etc/redis/redis.conf && \
    chmod 0555 /usr/local/bin/redis-hardened-entrypoint

USER redis:redis
WORKDIR /data

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
    CMD REDISCLI_AUTH="$REDIS_PASSWORD" redis-cli --no-auth-warning ping | grep -qx PONG

ENTRYPOINT ["/usr/local/bin/redis-hardened-entrypoint"]
CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]
