# Dockerfile для pytest тестов
FROM python:3.11-slim

WORKDIR /tests

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование тестов
COPY . .

# Команда по умолчанию
CMD ["pytest", "-v"]

