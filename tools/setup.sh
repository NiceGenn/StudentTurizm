#!/usr/bin/env bash
# Первичная настройка проекта: окружение, зависимости, база, демо-контент.
#
#   ./tools/setup.sh
#
# По умолчанию используется SQLite. Для PostgreSQL задайте переменные
# окружения DB_ENGINE=postgres, DB_NAME, DB_USER, DB_PASSWORD перед запуском.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ ! -d .venv ]; then
  echo "==> Создаю виртуальное окружение .venv"
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> Устанавливаю зависимости"
pip install --upgrade pip >/dev/null
pip install -r sources/requirements.txt

echo "==> Применяю миграции"
python sources/manage.py migrate

echo "==> Загружаю демонстрационное наполнение"
python sources/manage.py seed_demo

echo "==> Компилирую переводы (если установлен gettext)"
python sources/manage.py compilemessages 2>/dev/null || \
  echo "    gettext не найден — используются готовые .mo из репозитория"

echo
echo "Готово. Запуск сервера:  ./tools/run.sh"
echo "Панель управления:       http://127.0.0.1:8000/admin/  (admin / admin12345)"
