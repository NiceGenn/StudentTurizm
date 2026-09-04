#!/usr/bin/env bash
# Запуск портала на macOS и Linux одной командой: ./start.sh
# Windows-аналог — START.bat в этой же папке.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

echo
echo " =============================================================="
echo "  Туристический портал Благовещенского муниципального округа"
echo " =============================================================="
echo

if ! command -v python3 >/dev/null 2>&1; then
  echo " Python 3 не найден. Установите его и запустите ./start.sh снова."
  echo " macOS:  brew install python"
  echo " Ubuntu: sudo apt install python3 python3-venv"
  exit 1
fi

if [ ! -x .venv/bin/python ]; then
  echo " [1/4] Создаю рабочее окружение. Это нужно только при первом запуске."
  python3 -m venv .venv
fi
VPY=.venv/bin/python

if [ ! -f .venv/.installed ]; then
  echo " [2/4] Устанавливаю Django и Pillow. Нужен интернет, займёт минуту."
  "$VPY" -m pip install --upgrade pip --quiet
  if compgen -G "wheels/*.whl" > /dev/null; then
    echo "       Найдена папка wheels — ставлю без интернета."
    "$VPY" -m pip install --quiet --no-index --find-links wheels Django Pillow
  else
    "$VPY" -m pip install --quiet -r sources/requirements.txt
  fi
  touch .venv/.installed
fi

"$VPY" sources/manage.py migrate --noinput > /dev/null

if [ ! -f .venv/.seeded ]; then
  echo " [3/4] Наполняю портал: объекты, события, маршруты, пользователи."
  "$VPY" sources/manage.py seed_demo
  touch .venv/.seeded
fi

URL="http://127.0.0.1:8000/"
cat <<INFO

 [4/4] Запускаю сайт. Браузер откроется сам через несколько секунд.

  Сайт:              $URL
  Панель управления: ${URL}admin/

  Администратор:     admin    / admin12345
  Контент-менеджер:  manager  / manager12345
  Пользователь:      ivanova  / demo12345

  Чтобы остановить сайт, нажмите Ctrl+C.
 --------------------------------------------------------------

INFO

( sleep 4
  if command -v open >/dev/null 2>&1; then open "$URL"
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL"
  fi ) >/dev/null 2>&1 &

exec "$VPY" sources/manage.py runserver 127.0.0.1:8000
