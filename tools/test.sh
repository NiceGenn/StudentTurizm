#!/usr/bin/env bash
# Проверки проекта: системные проверки Django, отсутствие незакоммиченных
# миграций, тесты и валидация справочника data/.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ -d .venv ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

echo "==> Валидация справочника data/"
python tools/check_data.py

echo "==> Системные проверки Django"
python sources/manage.py check

echo "==> Проверка, что модели и миграции совпадают"
python sources/manage.py makemigrations --check --dry-run

echo "==> Тесты"
# Без явных меток Django ищет тесты от текущего каталога, поэтому
# перечисляем приложения сами.
if [ "$#" -gt 0 ]; then
  python sources/manage.py test "$@"
else
  python sources/manage.py test catalog accounts
fi
