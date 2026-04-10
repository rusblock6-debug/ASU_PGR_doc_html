#!/bin/sh
set -e

echo "Ожидание готовности MinIO через mc..."

i=0
until mc alias set myminio "${MINIO_HOST}" "${MINIO_ROOT_USER}" "${MINIO_ROOT_PASSWORD}" >/dev/null 2>&1; do
  i=$((i+1))
  if [ "$i" -ge 60 ]; then
    echo "MinIO не поднялся за ~60 попыток"
    exit 1
  fi
  echo "MinIO ещё не готов... ждём 3 сек"
  sleep 3
done

echo "MinIO готов → настраиваем"

# Проверяем наличие jq для парсинга JSON
if ! command -v jq >/dev/null 2>&1; then
  echo "jq не найден, устанавливаем..."
  apk add --no-cache jq >/dev/null 2>&1 || (echo "Не удалось установить jq" && exit 1)
fi

# Читаем bucket_names из JSON файла
BUCKET_CONFIG_FILE="${BUCKET_CONFIG_FILE:-/buckets.json}"
if [ ! -f "$BUCKET_CONFIG_FILE" ]; then
  echo "Ошибка: файл конфигурации бакетов не найден: $BUCKET_CONFIG_FILE"
  exit 1
fi

echo "Читаем конфигурацию бакетов из $BUCKET_CONFIG_FILE"
BUCKET_NAMES=$(jq -r '.bucket_names[]' "$BUCKET_CONFIG_FILE" 2>/dev/null)

if [ -z "$BUCKET_NAMES" ]; then
  echo "Ошибка: не удалось прочитать bucket_names из $BUCKET_CONFIG_FILE"
  exit 1
fi

# Настраиваем AMQP target (один раз для всех бакетов)
if [ -n "${AMQP_ARN_ID}" ] && [ -n "${AMQP_URL}" ]; then
  echo "Настраиваем AMQP target notify_amqp:${AMQP_ARN_ID}"
  mc admin config set myminio notify_amqp:${AMQP_ARN_ID} \
    url="${AMQP_URL}" \
    exchange="${AMQP_EXCHANGE:-minio.events}" \
    routing_key="${AMQP_ROUTING_KEY:-minio.events}" \
    exchange_type="${AMQP_EXCHANGE_TYPE:-topic}" \
    durable="${AMQP_DURABLE:-on}" \
    enable="on"

  mc admin service restart myminio --json
  sleep 3
fi

# Создаем бакеты в цикле
for BUCKET_NAME in $BUCKET_NAMES; do
  echo ""
  echo "=== Обработка бакета: ${BUCKET_NAME} ==="
  
  # Создаем бакет
  echo "Создаем бакет: ${BUCKET_NAME}"
  mc mb "myminio/${BUCKET_NAME}" --ignore-existing || true
  
  # Настраиваем события только если заданы AMQP параметры
  if [ -n "${AMQP_ARN_ID}" ] && [ -n "${AMQP_URL}" ]; then
    echo "Проверяем существующие правила уведомлений для bucket ${BUCKET_NAME}"
    mc event list "myminio/${BUCKET_NAME}" || true
    
    echo "Удаляем все существующие правила уведомлений для bucket ${BUCKET_NAME}"
    mc event remove "myminio/${BUCKET_NAME}" --force || true
    
    echo "Добавляем события ${EVENTS:-put} → AMQP (${AMQP_ARN_ID})"
    mc event add "myminio/${BUCKET_NAME}" \
      "arn:minio:sqs::${AMQP_ARN_ID}:amqp" \
      --event "${EVENTS:-put}"
    
    echo "Проверяем настроенные события для bucket ${BUCKET_NAME}"
    mc event list "myminio/${BUCKET_NAME}"
  else
    echo "AMQP параметры не заданы, пропускаем настройку событий для ${BUCKET_NAME}"
  fi
  
  echo "Бакет ${BUCKET_NAME} настроен успешно!"
done

echo ""
echo "Настройка всех бакетов завершена успешно!"
