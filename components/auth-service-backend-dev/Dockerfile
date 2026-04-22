# Используем официальный Python образ
FROM registry.dmi-msk.ru/base-images:python3.13-slim-master

# Настраиваем зеркало Selectel для Debian Bookworm
RUN echo "deb http://mirror.selectel.ru/debian/ bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb http://mirror.selectel.ru/debian/ bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb http://mirror.selectel.ru/debian-security/ bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir --index-url=https://mirrors.ustc.edu.cn/pypi/simple/ -r requirements.txt

# Копируем исходный код приложения
COPY . .

# Открываем порт, который будет использовать приложение
EXPOSE 8000

# Запускаем приложение с Uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
