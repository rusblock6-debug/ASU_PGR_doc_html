#!/bin/bash
set -e

# Функция для проверки статуса
check_vault_status() {
    curl -s -o /dev/null -w "%{http_code}" http://localhost:8200/v1/sys/health
}

# ШАГ 1: ЗАПУСКАЕМ VAULT В ФОНЕ
echo "Starting Vault server..."
vault server -config=/vault/config/config.hcl &
VAULT_PID=$!

# ШАГ 2: ЖДЕМ, ПОКА API СТАНЕТ ДОСТУПЕН
echo "Waiting for Vault API to become responsive..."
MAX_RETRIES=60
RETRY_COUNT=0
while ! curl -s http://localhost:8200/v1/sys/health >/dev/null 2>&1; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "ERROR: Vault API not responding after $MAX_RETRIES seconds"
        exit 1
    fi
    sleep 1
done
echo "Vault API is now responsive."

# ШАГ 3: СОЗДАЕМ ДИРЕКТОРИЮ ДЛЯ ДАННЫХ
mkdir -p /vault/data

# ШАГ 4: ПРОВЕРЯЕМ СТАТУС
STATUS_CODE=$(check_vault_status)
echo "Vault health status code: $STATUS_CODE"

case $STATUS_CODE in
    200)
        echo "Vault is already initialized and unsealed"
        ;;
    429)
        echo "Vault is unsealed and in standby mode"
        ;;
    501)
        echo "Vault is uninitialized. Initializing..."

        # Инициализируем Vault
        vault operator init \
            -key-shares=1 \
            -key-threshold=1 \
            -format=json > /vault/data/init.json


        # Сохраняем ключи
        jq -r '.root_token' /vault/data/init.json > /vault/data/root_token
        jq -r '.unseal_keys_b64[0]' /vault/data/init.json > /vault/data/unseal_key

        echo "Initialization complete. Root token and unseal key saved."

        # Распечатываем токен для удобства
        echo "Root Token: $(cat /vault/data/root_token)"
        echo "Unseal Key: $(cat /vault/data/unseal_key)"

        # Распечатываем Vault
        echo "Unsealing Vault..."
        vault operator unseal "$(cat /vault/data/unseal_key)"
        ;;

    503)
        echo "Vault is sealed. Unsealing..."
        if [ -f /vault/data/unseal_key ]; then
            vault operator unseal "$(cat /vault/data/unseal_key)"
        else
            echo "ERROR: Unseal key not found at /vault/data/unseal_key"
            exit 1
        fi
        ;;

    *)
        echo "Unknown Vault status code: $STATUS_CODE"
        # Показываем полный ответ для диагностики
        curl -v http://localhost:8200/v1/sys/health
        exit 1
        ;;
esac

# ШАГ 5: ПРОВЕРЯЕМ ФИНАЛЬНЫЙ СТАТУС
FINAL_STATUS=$(check_vault_status)
echo "Final Vault status code: $FINAL_STATUS"

if [ "$FINAL_STATUS" == "200" ] || [ "$FINAL_STATUS" == "429" ]; then
    echo "Vault is ready and unsealed!"

    export VAULT_TOKEN=$(cat /vault/data/root_token 2>/dev/null || echo "")
    echo "VAULT_TOKEN"
    echo $VAULT_TOKEN
    if [ -n "$VAULT_TOKEN" ]; then
        echo "Testing Vault access with root token..."
        vault secrets list >/dev/null 2>&1 && echo "Vault access successful!"
    fi
else
    echo "WARNING: Vault is not in ready state. Final status: $FINAL_STATUS"
fi

# ШАГ 6: ЖДЕМ ЗАВЕРШЕНИЯ ПРОЦЕССА VAULT
wait $VAULT_PID