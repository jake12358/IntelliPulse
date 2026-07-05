#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

kill_pid_or_group() {
  local pid="$1"
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
    kill -TERM "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null || true
  fi
}

if [ -d ".runtime" ]; then
  for file in .runtime/frontend.pid .runtime/celery.pid .runtime/api.pid; do
    if [ -f "$file" ]; then
      kill_pid_or_group "$(cat "$file")"
      rm -f "$file"
    fi
  done
fi

pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "celery -A app.tasks.celery_app.celery_app worker" 2>/dev/null || true
pkill -f "node.*/vite.*--host 0.0.0.0" 2>/dev/null || true
pkill -f "vite.*--host 0.0.0.0" 2>/dev/null || true

echo "IntelliPulse dev processes stopped."
