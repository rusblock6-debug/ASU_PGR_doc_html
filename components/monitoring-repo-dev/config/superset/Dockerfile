FROM dockerhub.timeweb.cloud/apache/superset:latest

USER root

# Установка драйвера Trino для подключения к Trino
RUN pip install --no-cache-dir trino==0.328.0

USER superset
