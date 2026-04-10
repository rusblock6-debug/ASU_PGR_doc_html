#!/bin/sh
set -e

echo "Ожидание готовности MinIO через mc..."

i=0
until mc alias set myminio "${MINIO_HOST}" "${MINIO_USER}" "${MINIO_PASSWORD}" >/dev/null 2>&1; do
  i=$((i+1))
  if [ "$i" -ge 60 ]; then
    echo "MinIO не поднялся за ~60 попыток"
    exit 1
  fi
  echo "MinIO ещё не готов... ждём 3 сек"
  sleep 3
done

echo "MinIO готов → настраиваем"

mc mb "myminio/${BUCKET_NAME}" --ignore-existing || true

echo "Настраиваем AMQP target notify_amqp:${AMQP_ARN_ID}"
mc admin config set myminio notify_amqp:${AMQP_ARN_ID} \
  url="${AMQP_URL}" \
  exchange="${AMQP_EXCHANGE}" \
  routing_key="${AMQP_ROUTING_KEY}" \
  exchange_type="${AMQP_EXCHANGE_TYPE:-topic}" \
  durable="${AMQP_DURABLE:-on}" \
  enable="on"

mc admin service restart myminio --json
sleep 3

mc event remove "myminio/${BUCKET_NAME}" "arn:minio:sqs::${AMQP_ARN_ID}:amqp" --force || true

echo "Добавляем события ${EVENTS} → AMQP (${AMQP_ARN_ID})"
mc event add "myminio/${BUCKET_NAME}" \
  "arn:minio:sqs::${AMQP_ARN_ID}:amqp" \
  --event "${EVENTS}"

echo "Настройка завершена успешно!"
mc event list "myminio/${BUCKET_NAME}"
