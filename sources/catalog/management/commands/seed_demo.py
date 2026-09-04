"""Загрузка демонстрационного наполнения портала из справочника data/.

    python manage.py seed_demo             # добавить/обновить контент
    python manage.py seed_demo --flush     # сначала очистить контент
    python manage.py seed_demo --no-images # без генерации изображений

Команда идемпотентна: повторный запуск обновляет записи, а не плодит копии.
"""

import datetime
import json
import random

from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from catalog.models import (
    Attraction,
    Category,
    Event,
    Favorite,
    Photo,
    Review,
    Route,
    RoutePoint,
    Village,
)
from portal import settings as portal_settings

DATA_DIR = portal_settings.DATA_DIR


def load(name):
    path = DATA_DIR / name
    if not path.exists():
        raise CommandError(f"Не найден файл справочника: {path}")
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def next_occurrence(month, day):
    """Ближайшая дата с указанными месяцем и днём: в этом году или в следующем.

    Благодаря этому демонстрационный календарь не устаревает: события
    всегда остаются предстоящими.
    """
    today = timezone.localdate()
    year = today.year
    try:
        candidate = datetime.date(year, month, day)
    except ValueError:  # 29 февраля в невисокосный год
        candidate = datetime.date(year, month, 28)
    if candidate < today:
        try:
            candidate = candidate.replace(year=year + 1)
        except ValueError:
            candidate = datetime.date(year + 1, month, 28)
    return candidate


class Command(BaseCommand):
    help = "Загружает демонстрационное наполнение портала из каталога data/"

    def add_arguments(self, parser):
        parser.add_argument("--flush", action="store_true", help="удалить существующий контент перед загрузкой")
        parser.add_argument("--no-images", action="store_true", help="не создавать изображения-заглушки")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["flush"]:
            self.stdout.write("Очистка контента…")
            Favorite.objects.all().delete()
            Review.objects.all().delete()
            RoutePoint.objects.all().delete()
            Route.objects.all().delete()
            Event.objects.all().delete()
            Photo.objects.all().delete()
            Attraction.objects.all().delete()
            Category.objects.all().delete()
            Village.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()
            Group.objects.filter(name="Контент-менеджеры").delete()

        villages = self.seed_villages()
        categories = self.seed_categories()
        attractions = self.seed_attractions(categories, villages)
        self.seed_events(attractions, villages)
        self.seed_routes(attractions)
        users = self.seed_users()
        self.seed_reviews(users, attractions)
        self.seed_favorites(users, attractions)

        if not options["no_images"]:
            self.seed_images(attractions)

        self.stdout.write(self.style.SUCCESS("Готово. Демонстрационное наполнение загружено."))
        self.stdout.write(
            "Учётные записи для демонстрации перечислены в data/demo_users.json "
            "(пароли учебные, менять их для реального развёртывания обязательно)."
        )

    # --- Справочники ------------------------------------------------------

    def seed_villages(self):
        result = {}
        for row in load("villages.json"):
            village, _created = Village.objects.update_or_create(
                slug=row["slug"],
                defaults={
                    "name": row["name"],
                    "name_en": row.get("name_en", ""),
                    "name_zh": row.get("name_zh", ""),
                    "description": row.get("description", ""),
                    "description_en": row.get("description_en", ""),
                    "description_zh": row.get("description_zh", ""),
                    "lat": row["lat"],
                    "lng": row["lng"],
                },
            )
            result[village.slug] = village
        self.stdout.write(f"Сёла: {len(result)}")
        return result

    def seed_categories(self):
        result = {}
        for row in load("categories.json"):
            category, _created = Category.objects.update_or_create(
                slug=row["slug"],
                defaults={
                    "name": row["name"],
                    "name_en": row.get("name_en", ""),
                    "name_zh": row.get("name_zh", ""),
                    "icon": row.get("icon", ""),
                    "color": row.get("color", "#2e7d32"),
                    "order": row.get("order", 100),
                },
            )
            result[category.slug] = category
        self.stdout.write(f"Категории: {len(result)}")
        return result

    def seed_attractions(self, categories, villages):
        result = {}
        for row in load("attractions.json"):
            village_slug = row.get("village")
            attraction, _created = Attraction.objects.update_or_create(
                slug=row["slug"],
                defaults={
                    "title": row["title"],
                    "title_en": row.get("title_en", ""),
                    "title_zh": row.get("title_zh", ""),
                    "category": categories[row["category"]],
                    "village": villages[village_slug] if village_slug else None,
                    "short_description": row["short_description"],
                    "short_description_en": row.get("short_description_en", ""),
                    "short_description_zh": row.get("short_description_zh", ""),
                    "description": row.get("description", ""),
                    "description_en": row.get("description_en", ""),
                    "description_zh": row.get("description_zh", ""),
                    "fact_note": row.get("fact_note", ""),
                    "lat": row["lat"],
                    "lng": row["lng"],
                    "address": row.get("address", ""),
                    "season": row.get("season", "all_year"),
                    "status": row.get("status", "active"),
                    "in_district": row.get("in_district", True),
                    "is_fictional": row.get("is_fictional", False),
                    "tags": ", ".join(row.get("tags", [])),
                    "is_published": row.get("is_published", True),
                },
            )
            result[attraction.slug] = attraction
        self.stdout.write(f"Объекты: {len(result)}")
        return result

    def seed_events(self, attractions, villages):
        count = 0
        for row in load("events.json"):
            start = next_occurrence(row["month"], row["day"])
            duration = max(int(row.get("days", 1)), 1)
            end = start + datetime.timedelta(days=duration - 1) if duration > 1 else None
            Event.objects.update_or_create(
                slug=row["slug"],
                defaults={
                    "title": row["title"],
                    "title_en": row.get("title_en", ""),
                    "title_zh": row.get("title_zh", ""),
                    "description": row.get("description", ""),
                    "description_en": row.get("description_en", ""),
                    "description_zh": row.get("description_zh", ""),
                    "fact_note": row.get("fact_note", ""),
                    "date_start": start,
                    "date_end": end,
                    "village": villages.get(row["village"]) if row.get("village") else None,
                    "attraction": attractions.get(row["attraction"]) if row.get("attraction") else None,
                    "is_published": True,
                },
            )
            count += 1
        self.stdout.write(f"События: {count}")

    def seed_routes(self, attractions):
        count = 0
        for row in load("routes.json"):
            route, _created = Route.objects.update_or_create(
                slug=row["slug"],
                defaults={
                    "title": row["title"],
                    "title_en": row.get("title_en", ""),
                    "title_zh": row.get("title_zh", ""),
                    "description": row.get("description", ""),
                    "description_en": row.get("description_en", ""),
                    "description_zh": row.get("description_zh", ""),
                    "duration": row.get("duration", ""),
                    "duration_en": row.get("duration_en", ""),
                    "duration_zh": row.get("duration_zh", ""),
                    "season": row.get("season", "all_year"),
                    "difficulty": row.get("difficulty", "easy"),
                    "is_published": True,
                },
            )
            route.points.all().delete()
            for index, point in enumerate(row.get("points", []), start=1):
                attraction = attractions.get(point["attraction"])
                if attraction is None:
                    raise CommandError(
                        f"Маршрут «{row['slug']}» ссылается на неизвестный объект «{point['attraction']}»"
                    )
                RoutePoint.objects.create(
                    route=route,
                    attraction=attraction,
                    order=index,
                    note=point.get("note", ""),
                )
            count += 1
        self.stdout.write(f"Маршруты: {count}")

    # --- Пользователи и UGC -----------------------------------------------

    def content_managers_group(self):
        """Группа «Контент-менеджеры» с правами на весь контент портала.

        Отметки `is_staff` мало: она открывает вход в панель, но без прав на
        модели разделы будут недоступны. Права выдаются группой, чтобы
        добавление нового менеджера сводилось к включению в неё.
        """
        group, _created = Group.objects.get_or_create(name="Контент-менеджеры")
        content_types = ContentType.objects.filter(app_label="catalog")
        group.permissions.set(Permission.objects.filter(content_type__in=content_types))
        return group

    def seed_users(self):
        group = self.content_managers_group()
        result = {}
        for row in load("demo_users.json"):
            user, created = User.objects.get_or_create(
                username=row["username"],
                defaults={
                    "first_name": row["first_name"],
                    "last_name": row["last_name"],
                    "email": row["email"],
                    "is_staff": row["is_staff"],
                    "is_superuser": row["is_superuser"],
                },
            )
            if created:
                user.set_password(row["password"])
                user.save()
            # Суперпользователю группа не нужна: у него права и так полные.
            if user.is_staff and not user.is_superuser:
                user.groups.add(group)
            result[user.username] = user
        self.stdout.write(f"Пользователи: {len(result)} (группа «{group.name}»: {group.user_set.count()})")
        return result

    def seed_reviews(self, users, attractions):
        count = 0
        for row in load("reviews.json"):
            user = users.get(row["user"])
            attraction = attractions.get(row["attraction"])
            if not user or not attraction:
                continue
            Review.objects.update_or_create(
                user=user,
                attraction=attraction,
                defaults={
                    "rating": row["rating"],
                    "text": row["text"],
                    "is_approved": row["is_approved"],
                    "created_at": timezone.now() - datetime.timedelta(days=row.get("days_ago", 0)),
                },
            )
            count += 1
        pending = Review.objects.filter(is_approved=False).count()
        self.stdout.write(f"Отзывы: {count} (из них на модерации: {pending})")

    def seed_favorites(self, users, attractions):
        """Немного избранного, чтобы личный кабинет не был пустым."""
        presets = {
            "ivanova": ["baza-otdyha-raduga", "smotrovaya-na-amur", "paseka-amurskiy-med"],
            "petrov": ["plyazh-ust-ivanovka", "most-blagoveshchensk-heihe"],
        }
        count = 0
        for username, slugs in presets.items():
            user = users.get(username)
            if not user:
                continue
            for slug in slugs:
                attraction = attractions.get(slug)
                if attraction:
                    Favorite.objects.get_or_create(user=user, attraction=attraction)
                    count += 1
        self.stdout.write(f"Избранное: {count}")

    # --- Изображения ------------------------------------------------------

    def seed_images(self, attractions):
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            self.stdout.write(self.style.WARNING("Pillow не установлен — изображения пропущены."))
            return

        created = 0
        for attraction in attractions.values():
            if attraction.photos.exists():
                continue
            for index in range(2):
                data = self.render_placeholder(
                    Image,
                    ImageDraw,
                    ImageFont,
                    title=attraction.title,
                    color=attraction.category.color,
                    seed=f"{attraction.slug}-{index}",
                    with_caption=(index == 0),
                )
                photo = Photo(
                    attraction=attraction,
                    caption=attraction.title if index == 0 else "",
                    is_cover=(index == 0),
                    order=index,
                )
                photo.image.save(f"{attraction.slug}-{index}.png", ContentFile(data), save=True)
                created += 1
        self.stdout.write(f"Изображения-заглушки: {created}")

    @staticmethod
    def render_placeholder(Image, ImageDraw, ImageFont, title, color, seed, with_caption):
        """Абстрактный пейзаж в цвете категории вместо настоящей фотографии.

        Настоящие снимки объектов нужно загрузить через панель управления:
        права на фотографии в учебном проекте не оформлялись.
        """
        import io

        width, height = 1200, 750
        rnd = random.Random(seed)
        base = tuple(int(color.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))

        def mix(a, b, t):
            return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

        image = Image.new("RGB", (width, height), "#ffffff")
        draw = ImageDraw.Draw(image)

        # Небо: вертикальный градиент от светлого оттенка категории к белому
        sky_top = mix(base, (255, 255, 255), 0.55)
        sky_bottom = mix(base, (255, 255, 255), 0.92)
        for y in range(height):
            draw.line([(0, y), (width, y)], fill=mix(sky_top, sky_bottom, y / height))

        # Солнце
        sun_x = rnd.randint(220, width - 220)
        sun_r = rnd.randint(50, 80)
        draw.ellipse(
            [sun_x - sun_r, 130 - sun_r, sun_x + sun_r, 130 + sun_r],
            fill=mix(base, (255, 245, 220), 0.75),
        )

        # Сопки: три силуэта разной насыщенности
        for layer in range(3):
            top = 380 + layer * 70
            points = [(0, height), (0, top + rnd.randint(-30, 30))]
            x = 0
            while x < width:
                x += rnd.randint(140, 240)
                points.append((min(x, width), top + rnd.randint(-70, 60)))
            points.append((width, height))
            draw.polygon(points, fill=mix(base, (255, 255, 255), 0.45 - layer * 0.18))

        # Река
        draw.rectangle([0, height - 110, width, height], fill=mix(base, (60, 110, 160), 0.6))

        if with_caption:
            draw.rectangle([0, height - 110, width, height - 110 + 6], fill=(255, 255, 255))
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
            except OSError:
                font = ImageFont.load_default()
            text = title if len(title) <= 42 else title[:41] + "…"
            draw.text((40, height - 78), text, font=font, fill=(255, 255, 255))

        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        return buffer.getvalue()
