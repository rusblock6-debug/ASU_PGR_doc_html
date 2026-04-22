#!/bin/sh
set -eu

: "${CLICKHOUSE_HOST:?required}"
: "${CLICKHOUSE_NATIVE_PORT:=9000}"
: "${CLICKHOUSE_DATABASE:?required}"
: "${CLICKHOUSE_USER:?required}"
: "${CLICKHOUSE_PASSWORD:?required}"

echo "Creating database if not exists: ${CLICKHOUSE_DATABASE}"

clickhouse-client \
  --host "${CLICKHOUSE_HOST}" \
  --port "${CLICKHOUSE_NATIVE_PORT}" \
  --user "${CLICKHOUSE_USER}" \
  --password "${CLICKHOUSE_PASSWORD}" \
  --query "CREATE DATABASE IF NOT EXISTS ${CLICKHOUSE_DATABASE}"

echo "Running migrations..."

exec migrate \
  -path /app/migrations \
  -database "clickhouse://${CLICKHOUSE_HOST}:${CLICKHOUSE_NATIVE_PORT}?database=${CLICKHOUSE_DATABASE}&username=${CLICKHOUSE_USER}&password=${CLICKHOUSE_PASSWORD}&x-multi-statement=true" \
  up