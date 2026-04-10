FROM upr-proxy.dmi-msk.ru/docker/python:3.11-slim

RUN echo "deb http://mirror.yandex.ru/debian bookworm main contrib non-free" > /etc/apt/sources.list && \
    echo "deb http://mirror.yandex.ru/debian bookworm-updates main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb http://mirror.yandex.ru/debian-security bookworm-security main contrib non-free" >> /etc/apt/sources.list

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копирование requirements.txt
COPY requirements.txt .

# Установка зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование приложения
COPY . .

# Запуск приложения
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8007"]
