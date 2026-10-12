#!/bin/bash
# WhyBot one-click launcher for macOS.
# Double-click in Finder (or run: bash ~/Desktop/whybot/WhyBot.command).
# First run installs everything (~2-4 min). Later runs start in seconds.
cd "$(dirname "$0")" || exit 1
ROOT="$(pwd)"
LOG="$ROOT/.logs"; mkdir -p "$LOG"
say() { printf "\n\033[1;35m▶ %s\033[0m\n" "$*"; }
fail() { printf "\n\033[1;31m✖ %s\033[0m\n" "$*"; read -r -p "Press Enter to close…"; exit 1; }

# Homebrew / conda paths so Finder launches see the same tools as Terminal
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.homebrew/bin:$HOME/anaconda3/bin:$HOME/miniconda3/bin:$PATH"

# ---- find Python 3.10+ ----------------------------------------------------------
PY=""
for c in python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then
    PY="$(command -v "$c")"; break
  fi
done
[ -n "$PY" ] || fail "Python 3.10+ not found. Install it with:  brew install python@3.12   (or from python.org), then run this again."
command -v node >/dev/null 2>&1 || fail "Node.js not found. Install it with:  brew install node   (or from nodejs.org), then run this again."
NODE_MAJOR=$(node -p 'process.versions.node.split(".")[0]')
[ "$NODE_MAJOR" -ge 18 ] || fail "Node 18+ needed (you have $(node -v)). Run: brew upgrade node"
say "Using $($PY --version) and Node $(node -v)"

# ---- free the ports if an old run is still going ------------------------------------
for port in 8000 3000; do
  pids=$(lsof -ti tcp:$port -sTCP:LISTEN 2>/dev/null)
  [ -n "$pids" ] && { say "Stopping old process on port $port"; kill $pids 2>/dev/null; sleep 1; }
done

# ---- backend --------------------------------------------------------------------------
if [ ! -x "$ROOT/.venv/bin/python" ]; then
  say "Creating Python environment (first run only)"
  "$PY" -m venv "$ROOT/.venv" || fail "Couldn't create the virtual environment."
fi
if [ ! -f "$ROOT/.venv/.installed" ] || [ "$ROOT/backend/requirements.txt" -nt "$ROOT/.venv/.installed" ]; then
  say "Installing Python packages"
  "$ROOT/.venv/bin/python" -m pip install -q --upgrade pip >"$LOG/pip.log" 2>&1
  "$ROOT/.venv/bin/python" -m pip install -q -r "$ROOT/backend/requirements.txt" >>"$LOG/pip.log" 2>&1 \
    || fail "pip install failed — see $LOG/pip.log"
  touch "$ROOT/.venv/.installed"
fi
[ -f "$ROOT/backend/.env" ] || cp "$ROOT/backend/.env.example" "$ROOT/backend/.env"

# ---- frontend -------------------------------------------------------------------------
cd "$ROOT/web" || fail "web folder missing"
if [ ! -d node_modules ] || [ package.json -nt node_modules ]; then
  say "Installing web packages (first run only)"
  npm ci --no-fund --no-audit >"$LOG/npm.log" 2>&1 || npm install --no-fund --no-audit >>"$LOG/npm.log" 2>&1 \
    || fail "npm install failed — see $LOG/npm.log"
  touch node_modules
fi
if [ ! -f .next/BUILD_ID ] || [ -n "$(find app components lib -newer .next/BUILD_ID -print -quit 2>/dev/null)" ]; then
  say "Building the web app"
  NEXT_TELEMETRY_DISABLED=1 npx next build >"$LOG/build.log" 2>&1 || fail "Build failed — see $LOG/build.log"
fi

# ---- start ----------------------------------------------------------------------------
say "Starting WhyBot engine on http://localhost:8000"
( cd "$ROOT/backend" && "$ROOT/.venv/bin/python" -m uvicorn main:app --host 127.0.0.1 --port 8000 >"$LOG/engine.log" 2>&1 ) &
ENGINE=$!
trap 'kill $ENGINE $WEB 2>/dev/null' EXIT INT TERM
for i in $(seq 1 30); do curl -s -o /dev/null http://127.0.0.1:8000/health && break; sleep 1; done
curl -s http://127.0.0.1:8000/health >/dev/null || fail "Engine didn't start — see $LOG/engine.log"

say "Starting web app on http://localhost:3000"
BACKEND_URL=http://127.0.0.1:8000 NEXT_TELEMETRY_DISABLED=1 npx next start -p 3000 >"$LOG/web.log" 2>&1 &
WEB=$!
for i in $(seq 1 30); do curl -s -o /dev/null http://127.0.0.1:3000/ && break; sleep 1; done

MODE=$(curl -s http://127.0.0.1:8000/health | "$ROOT/.venv/bin/python" -c 'import sys,json; d=json.load(sys.stdin); print(d["mode"], d["llm"])' 2>/dev/null)
say "WhyBot is running →  http://localhost:3000   (engine: $MODE)"
echo "   Add your keys in: $ROOT/backend/.env   then close this window and double-click WhyBot.command again."
echo "   Logs: $LOG    ·   Close this window (or press Ctrl+C) to stop."
open "http://localhost:3000" 2>/dev/null
wait $WEB
