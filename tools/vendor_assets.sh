#!/usr/bin/env bash
# Скачивает Bootstrap и Leaflet в sources/static/vendor/, чтобы сайт
# работал без интернета — например, на защите проекта.
#
# После запуска шаблоны автоматически переключаются на локальные файлы:
# настройка VENDOR_LOCAL в sources/portal/settings.py проверяет наличие
# sources/static/vendor/leaflet.js.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$ROOT/sources/static/vendor"
BS="5.3.3"
LEAFLET="1.9.4"

mkdir -p "$DEST/images"

get() {
  echo "    $2"
  curl -fsSL "$1" -o "$DEST/$2"
}

echo "==> Bootstrap $BS"
get "https://cdn.jsdelivr.net/npm/bootstrap@${BS}/dist/css/bootstrap.min.css" "bootstrap.min.css"
get "https://cdn.jsdelivr.net/npm/bootstrap@${BS}/dist/js/bootstrap.bundle.min.js" "bootstrap.bundle.min.js"

echo "==> Leaflet $LEAFLET"
get "https://cdn.jsdelivr.net/npm/leaflet@${LEAFLET}/dist/leaflet.css" "leaflet.css"
get "https://cdn.jsdelivr.net/npm/leaflet@${LEAFLET}/dist/leaflet.js" "leaflet.js"
for img in marker-icon.png marker-icon-2x.png marker-shadow.png layers.png layers-2x.png; do
  get "https://cdn.jsdelivr.net/npm/leaflet@${LEAFLET}/dist/images/${img}" "images/${img}"
done

echo
echo "Готово. Библиотеки лежат в sources/static/vendor/."
echo "Внимание: тайлы карты всё равно загружаются с серверов OpenStreetMap,"
echo "поэтому полностью офлайн карта работать не будет."
