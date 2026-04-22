FROM registry.dmi-msk.ru/base-images:python3.13-slim-master

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
RUN pip install --no-cache-dir --index-url=https://mirrors.ustc.edu.cn/pypi/simple/ -r requirements.txt

# Копирование приложения
COPY . .

# Права для запуска приложения скриптом
RUN chmod +x /app/scripts/entrypoint.sh

# Запуск приложения
ENTRYPOINT ["scripts/entrypoint.sh"]
