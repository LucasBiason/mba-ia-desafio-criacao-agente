#!/bin/sh
set -eu

case "${1:-prod}" in
  dev|runserver|prod)
    mode="${1:-prod}"
    if [ "$#" -gt 0 ]; then shift; fi
    if [ "$mode" = prod ]; then
      set -- --workers "${WORKERS:-1}" "$@"
    else
      set -- --reload --reload-dir /app/services "$@"
    fi
    exec uvicorn "$APP_MODULE" --host 0.0.0.0 --port "${PORT:-8000}" \
      --root-path "${ROOT_PATH:-}" --no-access-log "$@"
    ;;
  initialize)
    shift
    exec python -m services.initialize "$@"
    ;;
  api)
    shift
    exec python -m services.agent.api "$@"
    ;;
  test)
    shift
    exec python -m pytest "$@"
    ;;
  *)
    echo 'Uso: entrypoint.sh dev|runserver|prod|initialize|api|test [argumentos]' >&2
    exit 2
    ;;
esac
