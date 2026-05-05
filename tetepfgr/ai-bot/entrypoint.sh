#!/bin/bash
set -e

echo "Waiting for Ollama..."
until curl -s http://ollama:11434/api/tags > /dev/null 2>&1; do
  echo "Ollama not ready, waiting..."
  sleep 3
done

echo "Ollama started"

# Check if phi4-mini model exists
if ! curl -s http://ollama:11434/api/tags | grep -q "phi4-mini"; then
  echo "Downloading phi4-mini model..."
  curl -X POST http://ollama:11434/api/pull -d '{"name":"phi4-mini"}'
  echo "Model phi4-mini downloaded"
else
  echo "Model phi4-mini already installed"
fi

echo "Starting AI-bot..."
exec "$@"
