#!/bin/sh
set -e

echo "=================================="
echo "Starting eKuiper with auto-init"
echo "=================================="

# Start eKuiper in background with custom paths
echo "Starting eKuiper server..."
cd /kuiper && ./bin/kuiperd -data /kuiper/data -etc /kuiper/etc -log /kuiper/log &
EKUIPER_PID=$!

# Wait for eKuiper to be ready
echo "Waiting for eKuiper to be ready..."
sleep 5

# Run initialization script
if [ -f /kuiper/init/init.sh ]; then
  echo "Running initialization script..."
  bash /kuiper/init/init.sh || echo "⚠️  Initialization script failed (non-fatal)"
else
  echo "⚠️  No initialization script found at /kuiper/init/init.sh"
fi

# Keep eKuiper process in foreground
echo "Bringing eKuiper to foreground..."
wait $EKUIPER_PID

