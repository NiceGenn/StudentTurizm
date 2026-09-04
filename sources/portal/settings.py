"""
Настройки проекта «Туристический портал Благовещенского муниципального округа».

Учебный проект. Все персональные данные пользователей вымышленные,
интеграций с государственными системами, платежей и реальных
бронирований в проекте нет.
"""

import os
from pathlib import Path

# sources/
BASE_DIR = Path(__file__).resolve().parent.parent
# Корень репозитория и справочник контента
REPO_DIR = BASE_DIR.parent
DATA_DIR = REPO_DIR / "data"


def env(name, default=""):
    return os.environ.get(name, default)


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "да"}


def env_list(name, default=""):
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# --- Безопасность ---------------------------------------------------------
# Для учебной разработки ключ имеет значение по умолчанию.
# Для любого развёртывания задайте переменную окружения DJANGO_SECRET_KEY.
SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-insecure-key-change-me-in-production")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1],testserver")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

if not DEBUG:
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SESSION_COOKIE_HTTPONLY = True
    X_FRAME_OPTIONS = "DENY"


# --- Приложения -----------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "catalog",
    "accounts",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "portal.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "catalog.context_processors.site_menu",
            ],
        },
    },
]

WSGI_APPLICATION = "portal.wsgi.application"


# --- База данных ----------------------------------------------------------
# По умолчанию — SQLite: проект запускается сразу после клонирования.
# Для работы на PostgreSQL (целевая СУБД по ТЗ) задайте DB_ENGINE=postgres.
if env("DB_ENGINE", "sqlite") == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DB_NAME", "turizm"),
            "USER": env("DB_USER", "turizm"),
            "PASSWORD": env("DB_PASSWORD", ""),
            "HOST": env("DB_HOST", "localhost"),
            "PORT": env("DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# --- Языки и время --------------------------------------------------------
LANGUAGE_CODE = "ru"
LANGUAGES = [
    ("ru", "Русский"),
    ("en", "English"),
    ("zh-hans", "中文"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "Asia/Yakutsk"  # UTC+9, время Амурской области
USE_I18N = True
USE_TZ = True

# Суффиксы полей перевода в моделях: язык -> окончание поля
TRANSLATION_FIELD_SUFFIXES = {
    "ru": "",
    "en": "_en",
    "zh-hans": "_zh",
}


# --- Статика и медиа ------------------------------------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Bootstrap и Leaflet подключаются из static/vendor, если файлы туда скачаны
# (tools/vendor_assets.sh), иначе — из CDN. Локальная копия нужна, чтобы сайт
# работал на защите без интернета.
VENDOR_LOCAL = (BASE_DIR / "static" / "vendor" / "leaflet.js").exists()

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# --- Аутентификация -------------------------------------------------------
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "catalog:home"
LOGOUT_REDIRECT_URL = "catalog:home"

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"


# --- Параметры портала ----------------------------------------------------
PORTAL = {
    "district_name": "Благовещенский муниципальный округ",
    "region_name": "Амурская область",
    # Центр карты по умолчанию — Благовещенск
    "map_center": [50.2907, 127.5272],
    "map_zoom": 10,
    "contact_email": "info@example.org",
    "items_per_page": 9,
}
