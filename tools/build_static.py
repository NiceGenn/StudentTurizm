#!/usr/bin/env python3
"""Сборка статической витрины портала для GitHub Pages.

GitHub Pages отдаёт только готовые файлы и не выполняет Python, поэтому
полноценный сайт там работать не может. Этот скрипт обходит публичные
страницы портала и сохраняет их как обычные HTML-файлы — получается
витрина: каталог, карточки, карта, маршруты, события и справочные
страницы на трёх языках. Вход, избранное, отзывы и панель управления в
витрину не попадают, они остаются только в полной версии.

    python tools/build_static.py                 # в каталог build/
    PAGES_PREFIX=/MyRepo python tools/build_static.py

Результат кладётся в build/ и публикуется workflow-ом .github/workflows/pages.yml.
"""

import os
import re
import shutil
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
BUILD_DIR = REPO_DIR / "build"
# Адрес сайта на GitHub Pages — https://<логин>.github.io/<репозиторий>/
PREFIX = os.environ.get("PAGES_PREFIX", "/StudentTurizm").rstrip("/")

# Языки: код Django -> папка в сборке
LANGUAGES = [("ru", ""), ("en", "en"), ("zh-hans", "zh")]

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "portal.settings")
os.environ["STATIC_DEMO"] = "1"
os.environ["DJANGO_SCRIPT_NAME"] = PREFIX
os.environ["DJANGO_DEBUG"] = "False"
os.environ.setdefault("DJANGO_SECRET_KEY", "static-build-only-key")
# Задаём до django.setup(): хранилище статики настраивается один раз при
# загрузке приложения, поменять путь позже уже нельзя.
os.environ["DJANGO_STATIC_ROOT"] = str(REPO_DIR / "build" / "static")
sys.path.insert(0, str(REPO_DIR / "sources"))

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.test import Client  # noqa: E402

from catalog.models import Attraction, Event, Route, Village  # noqa: E402


def public_urls():
    """Адреса, которые попадают в витрину."""
    urls = [
        "/",
        "/catalog/",
        "/map/",
        "/routes/",
        "/events/",
        "/about/",
        "/how-to-get/",
        "/contacts/",
        "/api/attractions.json",
    ]
    urls += [f"/catalog/{slug}/" for slug in Attraction.objects.published().values_list("slug", flat=True)]
    urls += [f"/routes/{slug}/" for slug in Route.objects.filter(is_published=True).values_list("slug", flat=True)]
    urls += [f"/events/{slug}/" for slug in Event.objects.filter(is_published=True).values_list("slug", flat=True)]
    urls += [f"/villages/{slug}/" for slug in Village.objects.values_list("slug", flat=True)]
    return urls


def target_path(url, folder):
    """Куда сохранить страницу: /catalog/ -> build/<lang>/catalog/index.html."""
    base = BUILD_DIR / folder if folder else BUILD_DIR
    if url.endswith("/"):
        return base / url.strip("/") / "index.html" if url != "/" else base / "index.html"
    return base / url.lstrip("/")


def localize_links(content, folder):
    """Добавляет языковую папку во внутренние ссылки.

    Статика и медиа общие для всех языков, поэтому их адреса не трогаем.
    """
    if not folder:
        return content
    pattern = re.compile(r'(["\'])' + re.escape(PREFIX) + r'/(?!static/|media/)')
    return pattern.sub(r"\g<1>" + PREFIX + f"/{folder}/", content)


def set_language_links(content, url):
    """Подставляет адреса той же страницы на других языках."""
    for code, folder in LANGUAGES:
        placeholder = "@@LANG_" + {"ru": "RU", "en": "EN", "zh-hans": "ZH"}[code] + "@@"
        target = PREFIX + (f"/{folder}" if folder else "") + url
        content = content.replace(placeholder, target)
    return content


def build():
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True)

    urls = public_urls()
    written = 0

    for code, folder in LANGUAGES:
        client = Client()
        client.cookies[settings.LANGUAGE_COOKIE_NAME] = code

        for url in urls:
            response = client.get(url)
            if response.status_code != 200:
                print(f"  пропущено {url} (код {response.status_code})")
                continue

            content = response.content.decode("utf-8")
            content = localize_links(content, folder)
            content = set_language_links(content, url)

            path = target_path(url, folder)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            written += 1

        print(f"  язык {code}: {len(urls)} адресов")

    # Статика и фотографии — общие для всех языков.
    from django.core.management import call_command

    static_root = Path(settings.STATIC_ROOT)
    call_command("collectstatic", interactive=False, verbosity=0)
    print(f"  статика: {sum(1 for _ in static_root.rglob('*') if _.is_file())} файлов")

    media_src = Path(settings.MEDIA_ROOT)
    if media_src.exists():
        shutil.copytree(media_src, BUILD_DIR / "media")
        print(f"  изображения: {sum(1 for _ in (BUILD_DIR / 'media').rglob('*') if _.is_file())} файлов")
    else:
        print("  изображения: нет — сначала выполните seed_demo")

    # Без этого файла GitHub Pages пропускает сборку через Jekyll.
    (BUILD_DIR / ".nojekyll").write_text("", encoding="utf-8")

    print(f"\nГотово: {written} страниц в {BUILD_DIR}")
    print(f"Адрес сайта будет: https://<логин>.github.io{PREFIX}/")


if __name__ == "__main__":
    print(f"Сборка витрины с префиксом {PREFIX}")
    build()
