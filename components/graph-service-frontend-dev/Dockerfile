# Multi-stage build для Frontend
# Stage 1: Build React application
FROM registry.dmi-msk.ru/base-images:node-18-alpine-master as builder

WORKDIR /app

# Build arguments для переменных окружения React
# Бортовой режим: обращаемся к локальному enterprise-service
ARG REACT_APP_ENTERPRISE_SERVICE_HOST=enterprise-service
ARG REACT_APP_ENTERPRISE_SERVICE_PORT=8001

# Build argument для режима работы: server (серверный) или onboard (бортовой)
ARG REACT_APP_MODE=server

# Build arguments для начальной позиции "гаража" (только для серверного режима)
ARG REACT_APP_GARAGE_LAT=0
ARG REACT_APP_GARAGE_LON=0
ARG REACT_APP_GARAGE_HEIGHT=0

# Установка переменных окружения для сборки
ENV REACT_APP_ENTERPRISE_SERVICE_HOST=$REACT_APP_ENTERPRISE_SERVICE_HOST
ENV REACT_APP_ENTERPRISE_SERVICE_PORT=$REACT_APP_ENTERPRISE_SERVICE_PORT
ENV REACT_APP_MODE=$REACT_APP_MODE
ENV REACT_APP_GARAGE_LAT=$REACT_APP_GARAGE_LAT
ENV REACT_APP_GARAGE_LON=$REACT_APP_GARAGE_LON
ENV REACT_APP_GARAGE_HEIGHT=$REACT_APP_GARAGE_HEIGHT

# Копирование package files
COPY package*.json ./

# Установка зависимостей (используем npm install, так как нет package-lock.json)
RUN npm install

# Копирование исходников
COPY . .

# Сборка production build
RUN npm run build

# Stage 2: Production image с Nginx
FROM registry.dmi-msk.ru/base-images:nginx-master

# Копирование собранного приложения (react-scripts использует ./build)
COPY --from=builder /app/build /usr/share/nginx/html

# Копирование Nginx конфигурации
COPY nginx.conf /etc/nginx/nginx.conf

# Expose port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost/health || exit 1

# Запуск Nginx
CMD ["nginx", "-g", "daemon off;"]

