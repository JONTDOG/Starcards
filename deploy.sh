#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ -d .git ]; then
  git pull --ff-only
fi

if docker compose ps -q starcards >/dev/null 2>&1 && [ -n "$(docker compose ps -q starcards)" ]; then
  docker compose stop starcards || true
  docker compose rm -f starcards || true
fi

docker compose build starcards
docker compose up -d starcards
docker compose up -d nginx
docker compose logs --tail=50 starcards nginx
