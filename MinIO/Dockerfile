FROM golang:1.25-alpine AS builder
RUN CGO_ENABLED=0 go install github.com/minio/minio@RELEASE.2025-10-15T17-29-55Z

FROM alpine:3.23
COPY --from=builder /go/bin/minio /usr/local/bin/minio
RUN addgroup -S minio && adduser -S -G minio minio && mkdir /data && chown minio:minio /data
USER minio
HEALTHCHECK --interval=5s --timeout=3s --start-period=10s --retries=12 \
    CMD wget -q -O /dev/null http://127.0.0.1:9000/minio/health/ready || exit 1
ENTRYPOINT ["minio", "server", "/data"]
