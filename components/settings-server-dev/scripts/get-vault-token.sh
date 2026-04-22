#!/bin/bash
set -e

# Получаем путь к volume vault_state
VOLUME_PATH=$(docker volume inspect settings-service_vault_state --format '{{.Mountpoint}}')

# Извлекаем токен (если volume существует)
if [ -f "$VOLUME_PATH/root_token" ]; then
  cat "$VOLUME_PATH/root_token"
else
  echo "❌ Vault не инициализирован. Запустите сначала Vault!" >&2
  exit 1
fi