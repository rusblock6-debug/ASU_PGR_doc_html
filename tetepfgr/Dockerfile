FROM node:18-alpine

WORKDIR /app

# Копирование package.json (если есть)
# COPY package*.json ./
# RUN npm install

# Копирование файлов
COPY . .

# Установка простого HTTP-сервера
RUN npm install -g http-server

EXPOSE 3000

CMD ["http-server", "-p", "3000", "-c-1"]
