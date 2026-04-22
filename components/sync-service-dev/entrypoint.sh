#!/bin/sh
set -e

export PYTHONPATH=/service/app:$PYTHONPATH

if [ "$MODE" = "dev" ]; then
    export PYTHONUNBUFFERED=1
    export PYTHONDEVMODE=1
fi

if [ "$MODE" = "dev" ]; then
    echo "Starting Sync Service in DEV mode (with autoreload)"
    exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
else
    echo "Starting Sync Service in PROD mode (single worker)"
    echo "WARNING: Multi-worker mode is not supported"
    echo "To scale horizontally, spawn more containers/pods in conjunction with MULTI_REPLICA_MODE"
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info
fi
