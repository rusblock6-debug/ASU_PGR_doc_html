#!/bin/bash
# Не используем set -e чтобы скрипт продолжал работу при ошибках

EKUIPER_HOST="localhost:9081"
VEHICLE_ID="${VEHICLE_ID:-4}"

echo "=================================="
echo "eKuiper Auto-Initialization"
echo "Vehicle ID: ${VEHICLE_ID}"
echo "=================================="

# Wait for eKuiper to start
echo "Waiting for eKuiper to start..."
RETRY_COUNT=0
MAX_RETRIES=30
while ! curl -s http://${EKUIPER_HOST}/ping > /dev/null 2>&1; do
  RETRY_COUNT=$((RETRY_COUNT + 1))
  if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
    echo "ERROR: eKuiper failed to start after ${MAX_RETRIES} attempts"
    return 1
  fi
  echo "  Attempt ${RETRY_COUNT}/${MAX_RETRIES}..."
  sleep 1
done
echo "✅ eKuiper is ready!"


# Register external service: graphService
echo ""
echo "=================================="
echo "Registering external service: graphService"
echo "=================================="

# Prepare graphService.zip
GRAPH_SERVICE_ZIP="/tmp/graphService.zip"
cd /kuiper/init
zip -q ${GRAPH_SERVICE_ZIP} graphService.json

# Register service
SERVICE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "http://${EKUIPER_HOST}/services" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"graphService\",\"file\":\"file://${GRAPH_SERVICE_ZIP}\"}")

HTTP_CODE=$(echo "$SERVICE_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$SERVICE_RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
  echo "✅ graphService registered successfully"
elif [ "$HTTP_CODE" = "400" ] && echo "$RESPONSE_BODY" | grep -q "already exists"; then
  echo "ℹ️  graphService already exists (skipping)"
else
  echo "⚠️  graphService registration returned HTTP ${HTTP_CODE}"
  echo "Response: ${RESPONSE_BODY}"
fi

# Verify external service
echo ""
echo "Verifying external service..."
FUNCTIONS=$(curl -s "http://${EKUIPER_HOST}/services/functions" | grep -o '"ServiceName":"graphService"' || true)
if [ -n "$FUNCTIONS" ]; then
  echo "✅ graphService function is available"
else
  echo "⚠️  graphService function not found"
fi

# Prepare ruleset with dynamic VEHICLE_ID substitution
echo ""
echo "Preparing ruleset with VEHICLE_ID=${VEHICLE_ID}..."
RULESET_TEMP="/tmp/ruleset_${VEHICLE_ID}.json"
sed "s/VEHICLE_ID_PLACEHOLDER/${VEHICLE_ID}/g" /kuiper/init/ruleset.json > ${RULESET_TEMP}

# Import ruleset (streams, tables, rules)
echo ""
echo "=================================="
echo "Importing ruleset (streams + rules)..."
echo "=================================="

IMPORT_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "http://${EKUIPER_HOST}/ruleset/import" \
  -H "Content-Type: application/json" \
  -d "{\"file\":\"file://${RULESET_TEMP}\"}")

HTTP_CODE=$(echo "$IMPORT_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$IMPORT_RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
  echo "✅ Ruleset imported successfully"
  echo "Response: ${RESPONSE_BODY}"
else
  echo "⚠️  Ruleset import returned HTTP ${HTTP_CODE}"
  echo "Response: ${RESPONSE_BODY}"
  # Not fatal - rules might already exist
fi

# Summary
echo ""
echo "=================================="
echo "Initialization Summary"
echo "=================================="

# Count streams
STREAMS_COUNT=$(curl -s "http://${EKUIPER_HOST}/streams" | grep -o '"' | wc -l)
echo "Streams: ${STREAMS_COUNT} registered"

# Count rules
RULES=$(curl -s "http://${EKUIPER_HOST}/rules")
RULES_COUNT=$(echo "$RULES" | grep -o '"id"' | wc -l)
echo "Rules: ${RULES_COUNT} registered"

# List rules
echo ""
echo "Active rules:"
echo "$RULES" | grep -o '"id":"[^"]*"' | sed 's/"id":"//g' | sed 's/"//g' | sed 's/^/  - /'

echo ""
echo "=================================="
echo "✅ eKuiper initialization complete!"
echo "=================================="
echo ""
echo "Data Flow:"
echo "1. External Nanomq → eKuiper Proxy → Local Nanomq /raw"
echo "2. Local /raw → eKuiper Downsample → Local /ds (~2 events/sec)"
echo "3. Local /ds → eKuiper Events → Event topics"
echo "4. GPS /ds → eKuiper (graphService) → Tag Detection"
echo "5. All MQTT topics → PostgreSQL (archive)"

