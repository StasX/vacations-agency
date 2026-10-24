FROM node:20-alpine3.19 AS builder
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
RUN npm run build


FROM nginx:1.30.6-alpine3.24

RUN apk upgrade --no-cache

COPY --from=builder /app/build/ /usr/share/nginx/html/
COPY nginx/nginx-main.conf /etc/nginx/nginx.conf
COPY nginx/entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh && \
    addgroup -S appgroup && \
    adduser -S appuser -G appgroup && \
    chown -R appuser:appgroup /var/cache/nginx && \
    chown -R appuser:appgroup /var/run && \
    chown -R appuser:appgroup /etc/nginx && \
    mkdir -p /var/log/nginx && \
    chown -R appuser:appgroup /var/log/nginx && \
    mkdir -p /tmp/nginx && \
    chown -R appuser:appgroup /tmp/nginx

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s \
    --start-period=10s --retries=3 \
    CMD sh -c 'wget -q -O /dev/null http://127.0.0.1:3000/ || exit 1'

USER appuser
ENTRYPOINT ["/entrypoint.sh"]
