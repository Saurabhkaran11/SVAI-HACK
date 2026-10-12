#!/usr/bin/env bash
# One command: FastAPI engine (port 8000) + Next.js web app (port 3000)
set -e
cd "$(dirname "$0")"
[ -d .venv ] && source .venv/bin/activate
[ -f backend/.env ] || cp backend/.env.example backend/.env

echo "▶ Starting WhyBot engine on http://localhost:8000"
(cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000) &
API_PID=$!
trap "kill $API_PID 2>/dev/null" EXIT

cd web
[ -d node_modules ] || npm install
if [ "$1" = "dev" ]; then
  echo "▶ Web app (dev mode) on http://localhost:3000"
  npm run dev
else
  [ -d .next ] || npm run build
  echo "▶ Web app on http://localhost:3000"
  npm run start
fi
