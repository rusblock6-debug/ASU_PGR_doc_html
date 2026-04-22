#!/bin/sh
set -e  # Автоматический выход при ошибке

echo "🔍 Checking vault_state volume..."
ls -la /vault_state || (echo "⚠️ Volume not mounted!" && exit 1)

echo '⏳ Waiting for Vault initialization...'
while ! curl -s http://dispatching-server-vault:8200/v1/sys/health 2>/dev/null | grep -q '"initialized":true'; do
  sleep 1
done

echo '⏳ Waiting for Vault unseal...'
while ! curl -s http://dispatching-server-vault:8200/v1/sys/health 2>/dev/null | grep -q '"sealed":false'; do
  sleep 1
done

echo "🔐 Loading Vault root token..."
if [ ! -f "/vault_state/root_token" ]; then
  echo "❌ ERROR: root_token file not found! Check Vault initialization."
  exit 1
fi

VAULT_TOKEN=$(cat /vault_state/root_token | tr -d '\n')
export VAULT_TOKEN

echo "🚀 Starting settings-service..."
exec uvicorn main:app --host 0.0.0.0 --port 8006
