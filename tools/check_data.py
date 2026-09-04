#!/usr/bin/env python3
"""Валидация справочника data/ до загрузки в базу.

Проверяет структуру JSON, уникальность кодов, ссылочную целостность
между файлами, диапазоны координат и допустимые значения статусов.
Запускается отдельно от Django, поэтому годится и для CI, и для
быстрой самопроверки перед коммитом:

    python tools/check_data.py
"""

import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

SEASONS = {"all_year", "summer", "winter", "spring_autumn"}
STATUSES = {"active", "construction", "planned", "closed"}
DIFFICULTIES = {"easy", "medium", "hard"}

# Границы Амурской области с запасом: грубая проверка «не перепутаны ли
# широта с долготой» и «не уехала ли точка в другой регион».
LAT_RANGE = (48.0, 57.0)
LNG_RANGE = (119.0, 135.0)

errors = []
warnings = []


def fail(message):
    errors.append(message)


def warn(message):
    warnings.append(message)


def load(name):
    path = DATA_DIR / name
    if not path.exists():
        fail(f"{name}: файл не найден")
        return []
    try:
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        fail(f"{name}: некорректный JSON — {exc}")
        return []


def check_unique(rows, key, name):
    seen = set()
    for row in rows:
        value = row.get(key)
        if value is None:
            fail(f"{name}: запись без поля «{key}»")
        elif value in seen:
            fail(f"{name}: повторяющееся значение {key}={value!r}")
        else:
            seen.add(value)
    return seen


def check_coords(row, name, label):
    lat, lng = row.get("lat"), row.get("lng")
    if lat is None or lng is None:
        fail(f"{name}: у «{label}» нет координат")
        return
    if not LAT_RANGE[0] <= lat <= LAT_RANGE[1]:
        fail(f"{name}: широта {lat} у «{label}» вне диапазона Амурской области")
    if not LNG_RANGE[0] <= lng <= LNG_RANGE[1]:
        fail(f"{name}: долгота {lng} у «{label}» вне диапазона Амурской области")


def check_translations(row, fields, name, label):
    for field in fields:
        for suffix, language in (("_en", "английский"), ("_zh", "китайский")):
            if not row.get(f"{field}{suffix}"):
                warn(f"{name}: «{label}» — нет перевода поля {field} на {language}")


def main():
    villages = load("villages.json")
    categories = load("categories.json")
    attractions = load("attractions.json")
    events = load("events.json")
    routes = load("routes.json")
    users = load("demo_users.json")
    reviews = load("reviews.json")

    village_slugs = check_unique(villages, "slug", "villages.json")
    category_slugs = check_unique(categories, "slug", "categories.json")
    attraction_slugs = check_unique(attractions, "slug", "attractions.json")
    check_unique(events, "slug", "events.json")
    check_unique(routes, "slug", "routes.json")
    user_names = check_unique(users, "username", "demo_users.json")

    for row in villages:
        check_coords(row, "villages.json", row.get("name", "?"))
        check_translations(row, ["name", "description"], "villages.json", row.get("name", "?"))

    for row in categories:
        color = row.get("color", "")
        if not (color.startswith("#") and len(color) == 7):
            fail(f"categories.json: у «{row.get('name')}» некорректный цвет {color!r}")

    for row in attractions:
        label = row.get("title", "?")
        check_coords(row, "attractions.json", label)
        check_translations(row, ["title", "short_description"], "attractions.json", label)

        if row.get("category") not in category_slugs:
            fail(f"attractions.json: «{label}» ссылается на неизвестную категорию {row.get('category')!r}")

        village = row.get("village")
        if village is not None and village not in village_slugs:
            fail(f"attractions.json: «{label}» ссылается на неизвестное село {village!r}")
        if village is None and row.get("in_district", True):
            fail(f"attractions.json: «{label}» без села должен быть помечен in_district = false")

        if row.get("season", "all_year") not in SEASONS:
            fail(f"attractions.json: «{label}» — недопустимая сезонность {row.get('season')!r}")
        if row.get("status", "active") not in STATUSES:
            fail(f"attractions.json: «{label}» — недопустимый статус {row.get('status')!r}")

        # Ключевое требование ТЗ: нерабочие и строящиеся объекты обязаны
        # нести пояснение, иначе портал введёт туриста в заблуждение.
        if row.get("status") in {"closed", "construction", "planned"} and not row.get("fact_note"):
            fail(f"attractions.json: «{label}» имеет статус {row.get('status')}, но без fact_note")
        if row.get("is_fictional") and not row.get("fact_note"):
            fail(f"attractions.json: «{label}» помечен как условный, но без fact_note")

    for row in events:
        label = row.get("title", "?")
        month, day = row.get("month"), row.get("day")
        if not (isinstance(month, int) and 1 <= month <= 12):
            fail(f"events.json: «{label}» — некорректный месяц {month!r}")
        if not (isinstance(day, int) and 1 <= day <= 31):
            fail(f"events.json: «{label}» — некорректный день {day!r}")
        if row.get("village") and row["village"] not in village_slugs:
            fail(f"events.json: «{label}» ссылается на неизвестное село {row['village']!r}")
        if row.get("attraction") and row["attraction"] not in attraction_slugs:
            fail(f"events.json: «{label}» ссылается на неизвестный объект {row['attraction']!r}")
        check_translations(row, ["title", "description"], "events.json", label)

    for row in routes:
        label = row.get("title", "?")
        if row.get("season", "all_year") not in SEASONS:
            fail(f"routes.json: «{label}» — недопустимый сезон {row.get('season')!r}")
        if row.get("difficulty", "easy") not in DIFFICULTIES:
            fail(f"routes.json: «{label}» — недопустимая сложность {row.get('difficulty')!r}")

        points = row.get("points", [])
        if len(points) < 2:
            fail(f"routes.json: в маршруте «{label}» меньше двух точек")

        seen_points = set()
        for point in points:
            slug = point.get("attraction")
            if slug not in attraction_slugs:
                fail(f"routes.json: «{label}» ссылается на неизвестный объект {slug!r}")
                continue
            if slug in seen_points:
                fail(f"routes.json: «{label}» содержит объект {slug!r} дважды")
            seen_points.add(slug)

            attraction = next(item for item in attractions if item["slug"] == slug)
            if attraction.get("status") != "active":
                fail(
                    f"routes.json: «{label}» включает объект «{attraction['title']}» "
                    f"со статусом «{attraction.get('status')}» — недействующие объекты "
                    "в маршруты включать нельзя"
                )
            if not attraction.get("in_district", True):
                fail(
                    f"routes.json: «{label}» включает объект «{attraction['title']}» "
                    "за пределами округа"
                )

    for row in reviews:
        if row.get("user") not in user_names:
            fail(f"reviews.json: отзыв ссылается на неизвестного пользователя {row.get('user')!r}")
        if row.get("attraction") not in attraction_slugs:
            fail(f"reviews.json: отзыв ссылается на неизвестный объект {row.get('attraction')!r}")
        rating = row.get("rating")
        if not (isinstance(rating, int) and 1 <= rating <= 5):
            fail(f"reviews.json: недопустимая оценка {rating!r}")

    print(
        f"Справочник: сёл {len(villages)}, категорий {len(categories)}, "
        f"объектов {len(attractions)}, событий {len(events)}, маршрутов {len(routes)}, "
        f"пользователей {len(users)}, отзывов {len(reviews)}."
    )

    for message in warnings:
        print(f"  предупреждение: {message}")
    for message in errors:
        print(f"  ОШИБКА: {message}")

    if errors:
        print(f"\nНайдено ошибок: {len(errors)}")
        return 1
    print("Ошибок нет.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
