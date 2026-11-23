#!/bin/sh
set -eu

case "${1:-}" in
  dev|runserver|prod)
    mode="$1"
    shift
    : "${APP_MODULE:?Defina o módulo ASGI do serviço.}"
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
  test)
    shift
    exec python -m pytest "$@"
    ;;
  *)
    echo 'Uso: entrypoint.sh dev|runserver|prod|initialize|test [argumentos]' >&2
    exit 2
    ;;
esac
