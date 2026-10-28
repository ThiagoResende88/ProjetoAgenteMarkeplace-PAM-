#!/bin/sh
# Sobe a demo local e o túnel Cloudflare; mantém os dois vivos enquanto o processo rodar.
set -eu
cd "$(dirname "$0")/.."
mkdir -p saidas/shopee_golive
python3 -m http.server 8080 --bind 127.0.0.1 --directory docs/shopee_golive > saidas/shopee_golive/server.log 2>&1 &
SERVER=$!
cleanup() { kill "$SERVER" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
./bin/cloudflared tunnel --url http://127.0.0.1:8080 --no-autoupdate > saidas/shopee_golive/tunnel.log 2>&1 &
TUNNEL=$!
cleanup2() { cleanup; kill "$TUNNEL" 2>/dev/null || true; }
trap cleanup2 EXIT INT TERM
wait "$TUNNEL"
