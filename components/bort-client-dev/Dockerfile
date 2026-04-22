
FROM registry.dmi-msk.ru/base-images:node-lts-alpine-master AS builder
WORKDIR /app
COPY package*.json .npmrc ./
RUN npm ci || true
COPY . .
RUN npm run build

FROM registry.dmi-msk.ru/base-images:nginx-master

RUN mkdir -p /run/nginx /usr/share/nginx/html /etc/nginx/http.d
WORKDIR /app
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx/nginx.default.conf /etc/nginx/conf.d/default.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
EXPOSE 5173 80
ENV APP_MODE=dev
ENTRYPOINT ["/entrypoint.sh"]