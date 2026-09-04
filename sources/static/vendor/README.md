# Сторонние библиотеки

Локальные копии, чтобы сайт работал без интернета — например, на защите.
Настройка `VENDOR_LOCAL` в `sources/portal/settings.py` проверяет наличие
`leaflet.js` и переключает шаблоны на эти файлы; если папку удалить,
шаблоны автоматически вернутся к CDN.

| Файл | Библиотека | Версия | Лицензия |
|---|---|---|---|
| `bootstrap.min.css`, `bootstrap.bundle.min.js` | [Bootstrap](https://getbootstrap.com/) | 5.3.3 | MIT |
| `leaflet.css`, `leaflet.js`, `images/*` | [Leaflet](https://leafletjs.com/) | 1.9.4 | BSD-2-Clause |

Обновить версии: `./tools/vendor_assets.sh` (правьте номера версий в скрипте).

Тайлы карты приходят с серверов OpenStreetMap и локально не хранятся:
без интернета карта останется серой, но сам сайт будет работать.
