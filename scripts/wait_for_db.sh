#!/usr/bin/env bash
# wait_for_db.sh <host> <port> <timeout_seconds>
set -euo pipefail
HOST=${1:-db}
PORT=${2:-5432}
TIMEOUT=${3:-60}

echo "Waiting for database ${HOST}:${PORT} (timeout ${TIMEOUT}s)"
start=$(date +%s)
while true; do
  if nc -z "$HOST" "$PORT" >/dev/null 2>&1; then
    echo "DB is accepting connections"
    exit 0
  fi
  now=$(date +%s)
  if [ $((now - start)) -ge "$TIMEOUT" ]; then
    echo "Timed out waiting for ${HOST}:${PORT}" >&2
    exit 1
  fi
  sleep 1
done
