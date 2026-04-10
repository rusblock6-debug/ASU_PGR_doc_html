#!/bin/sh
set -e

# ===== CONFIG =====
RABBITMQ_HOST="${RABBITMQ_HOST:-rabbitmq}"
RABBITMQ_PORT="${RABBITMQ_PORT:-15672}"
RABBITMQ_USER="${RABBITMQ_USER:-rabbit}"
RABBITMQ_PASS="${RABBITMQ_PASS:-rabbit}"

# vhost "/" должен быть URL-encoded
VHOST="${VHOST:-%2F}"

EXCHANGE="${EXCHANGE:-minio.events}"
EXCHANGE_TYPE="${EXCHANGE_TYPE:-topic}"

QUEUE="${QUEUE:-minio-events}"
ROUTING_KEY="${ROUTING_KEY:-minio.*}"

DURABLE="${DURABLE:-true}"
# ===================

echo "Waiting for RabbitMQ Management API..."

i=0
until curl -fsS -u "$RABBITMQ_USER:$RABBITMQ_PASS" \
  "http://$RABBITMQ_HOST:$RABBITMQ_PORT/api/overview" >/dev/null; do
  i=$((i+1))
  if [ "$i" -ge 60 ]; then
    echo "RabbitMQ API not ready after ~120 seconds"
    exit 1
  fi
  echo "RabbitMQ not ready yet... waiting 2s"
  sleep 2
done

echo "RabbitMQ API is ready"

echo "Creating exchange: $EXCHANGE"
curl -fsS -u "$RABBITMQ_USER:$RABBITMQ_PASS" \
  -H "content-type: application/json" \
  -X PUT \
  "http://$RABBITMQ_HOST:$RABBITMQ_PORT/api/exchanges/$VHOST/$EXCHANGE" \
  -d "{
    \"type\": \"$EXCHANGE_TYPE\",
    \"durable\": $DURABLE,
    \"auto_delete\": false,
    \"internal\": false,
    \"arguments\": {}
  }"

echo "Creating queue: $QUEUE"
curl -fsS -u "$RABBITMQ_USER:$RABBITMQ_PASS" \
  -H "content-type: application/json" \
  -X PUT \
  "http://$RABBITMQ_HOST:$RABBITMQ_PORT/api/queues/$VHOST/$QUEUE" \
  -d "{
    \"durable\": $DURABLE,
    \"auto_delete\": false,
    \"arguments\": {}
  }"

echo "Binding queue '$QUEUE' -> exchange '$EXCHANGE' (routing_key=$ROUTING_KEY)"
curl -fsS -u "$RABBITMQ_USER:$RABBITMQ_PASS" \
  -H "content-type: application/json" \
  -X POST \
  "http://$RABBITMQ_HOST:$RABBITMQ_PORT/api/bindings/$VHOST/e/$EXCHANGE/q/$QUEUE" \
  -d "{
    \"routing_key\": \"$ROUTING_KEY\",
    \"arguments\": {}
  }"

echo "RabbitMQ init completed successfully"
