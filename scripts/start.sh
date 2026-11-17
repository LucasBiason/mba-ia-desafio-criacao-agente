#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
python3 scripts/setup-local.py
docker compose up --build --wait "$@"
