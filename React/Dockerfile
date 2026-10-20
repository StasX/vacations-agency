FROM node:20-alpine3.19 as builder
WORKDIR /app
ADD package.json /app
RUN npm i
COPY . /app
ENTRYPOINT npm start

FROM nginx:alpine

COPY --from=builder /app/dist/ /usr/share/nginx/html/
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

RUN chown -R appuser:appgroup /app
USER appuser
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5001/health || exit 1

EXPOSE 80