FROM registry.dmi-msk.ru/base-images:node22-alpine-master AS builder
WORKDIR /app
COPY package*.json .npmrc ./
RUN npm ci || true
COPY . .

FROM registry.dmi-msk.ru/base-images:nginx-master
WORKDIR /app
RUN mkdir -p /run/nginx /usr/share/nginx/html /etc/nginx/http.d
COPY --from=builder /app /app
COPY nginx/nginx.default.conf /etc/nginx/conf.d/default.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
EXPOSE 5173 80
ENV APP_MODE=dev
ENTRYPOINT ["/entrypoint.sh"]