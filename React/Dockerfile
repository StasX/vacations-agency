FROM node:20-alpine3.19
WORKDIR /app
ADD package.json /app
RUN npm i
COPY . /app
ENTRYPOINT npm start

FROM nginx:alpine

COPY --from=build /app/dist/ /usr/share/nginx/html/
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80