#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -f ".env" ]; then
  cp .env.example .env
fi

mkdir -p .runtime

API_PID=""
CELERY_PID=""
FRONTEND_PID=""

kill_group() {
  local pid="$1"
  if [ -n "$pid" ]; then
    kill -TERM "-$pid" 2>/dev/null || kill "$pid" 2>/dev/null || true
  fi
}

cleanup() {
  kill_group "$FRONTEND_PID"
  kill_group "$CELERY_PID"
  kill_group "$API_PID"
  rm -f .runtime/api.pid .runtime/celery.pid .runtime/frontend.pid
}
trap cleanup INT TERM EXIT

docker compose up -d redis-stack postgres

CELERY_AVAILABLE=0
if [ "${INTELLIPULSE_TASK_MODE:-}" = "local" ]; then
  echo "INTELLIPULSE_TASK_MODE=local is set. Upload tasks will run in local synchronous mode."
elif python -c "import redis; import kombu.transport.redis" >/dev/null 2>&1; then
  CELERY_AVAILABLE=1
else
  export INTELLIPULSE_TASK_MODE=local
  echo "Celery Redis transport is unavailable. Upload tasks will run in local synchronous mode."
  echo "Run: python -m pip install --upgrade 'celery[redis]>=5.3,<6' 'redis>=5,<6' 'kombu>=5.3,<6'"
  echo "For details, run: python scripts/diagnose_runtime.py"
fi

setsid python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!
echo "$API_PID" > .runtime/api.pid

for _ in $(seq 1 30); do
  if python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=1)" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if [ "$CELERY_AVAILABLE" = "1" ]; then
  setsid env C_FORCE_ROOT=1 python -m celery -A app.tasks.celery_app.celery_app worker --loglevel=info &
  CELERY_PID=$!
  echo "$CELERY_PID" > .runtime/celery.pid
fi

cd frontend
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
if ! command -v node >/dev/null 2>&1; then
  echo "Node.js is not installed in this WSL environment."
  echo "Install Node.js in WSL, then run: cd frontend && npm install"
  echo "Example with nvm: nvm install --lts && nvm use --lts"
  exit 1
fi
if ! node -e "const [major]=process.versions.node.split('.').map(Number); process.exit(major >= 20 ? 0 : 1)" >/dev/null 2>&1; then
  echo "Node.js $(node --version) is too old for the installed Vite version."
  echo "Install Node.js 20+ in WSL, then run: cd frontend && npm install"
  echo "Example with nvm: nvm install 20 && nvm use 20"
  exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "npm is not installed in this WSL environment."
  exit 1
fi
if [ ! -x "./node_modules/.bin/vite" ]; then
  echo "frontend/node_modules is missing. Run: cd frontend && npm install"
  exit 1
fi
setsid ./node_modules/.bin/vite --host 0.0.0.0 --port "$FRONTEND_PORT" --strictPort &
FRONTEND_PID=$!
echo "$FRONTEND_PID" > ../.runtime/frontend.pid
echo "Frontend URL: http://localhost:${FRONTEND_PORT}/"

wait
