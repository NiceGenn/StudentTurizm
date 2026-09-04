#!/usr/bin/env bash
# Запуск сервера разработки.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ -d .venv ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

exec python sources/manage.py runserver "${1:-127.0.0.1:8000}"
