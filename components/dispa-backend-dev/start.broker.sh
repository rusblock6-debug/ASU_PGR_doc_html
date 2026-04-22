#! /bin/bash

if [ "$1" = "bort" ]; then
  if [ -z "$2" ]; then
    echo "Ошибка: в режиме bort необходимо передать второй аргумент" >&2
    exit 1
  fi
  echo "Запуск в режиме борта. Борт № $2"
  export SERVICE_MODE=bort
  export VEHICLE_ID="$2"
  faststream run app.services.rabbitmq.bort.app:app
elif [ "$1" = "server" ]; then
  echo "Запуск в режиме сервера"
  export SERVICE_MODE=server
  faststream run app.services.rabbitmq.server.app:app
else
  echo "Переданный режим $1 не поддерживается"
fi
