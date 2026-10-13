#!/bin/sh
# Start the engine on an internal port, wait until healthy, then serve the web app on $PORT.
# If either process exits, the container exits so the platform restarts it.
set -e
# Never send internal localhost traffic through an outbound proxy.
export NO_PROXY="127.0.0.1,localhost${NO_PROXY:+,$NO_PROXY}" no_proxy="127.0.0.1,localhost${no_proxy:+,$no_proxy}"
cd /app/backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000 &
ENGINE=$!

i=0
until python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)" 2>/dev/null; do
  i=$((i+1)); [ "$i" -gt 60 ] && { echo "engine failed to start"; exit 1; }
  kill -0 "$ENGINE" 2>/dev/null || { echo "engine exited"; exit 1; }
  sleep 1
done
echo "engine ready; starting web on :${PORT:-3000}"

cd /app/web
node node_modules/next/dist/bin/next start -H 0.0.0.0 -p "${PORT:-3000}" &
WEB=$!

trap 'kill $ENGINE $WEB 2>/dev/null' INT TERM
while kill -0 "$ENGINE" 2>/dev/null && kill -0 "$WEB" 2>/dev/null; do sleep 2; done
echo "a process exited; stopping container"
kill $ENGINE $WEB 2>/dev/null || true
exit 1
