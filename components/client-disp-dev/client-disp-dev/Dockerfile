FROM mirror.gcr.io/library/node:22-alpine
RUN apk add --no-cache nginx && mkdir -p /run/nginx /usr/share/nginx/html /etc/nginx/http.d
WORKDIR /app
COPY package*.json .npmrc ./ 
RUN npm ci || true
COPY . .
COPY nginx/nginx.default.conf /etc/nginx/http.d/default.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
EXPOSE 5173 80
ENV APP_MODE=dev
ENTRYPOINT ["/entrypoint.sh"]