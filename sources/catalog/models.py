"""Модели предметной области портала.

Схема соответствует ER-модели из docs/03-er-model.md:

    Village 1—N Attraction        Attraction 1—N Photo
    Category 1—N Attraction       Attraction 1—N Review
    Route N—M Attraction          Attraction 1—N Favorite
        (через RoutePoint)        Event N—1 Village, N—1 Attraction (необяз.)
"""

from django.conf import settings
from django.db import models
from django.db.models import Avg, Count
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import get_language


class TranslatedFieldsMixin:
    """Выбор языковой версии поля по активному языку интерфейса.

    В моделях хранятся поля `title`, `title_en`, `title_zh`. Метод `tr()`
    возвращает версию для текущего языка, а при пустом переводе —
    русский оригинал, чтобы страница никогда не оказалась пустой.
    """

    def tr(self, field_name):
        suffixes = getattr(settings, "TRANSLATION_FIELD_SUFFIXES", {})
        language = get_language() or settings.LANGUAGE_CODE
        suffix = suffixes.get(language)
        if suffix is None:
            # 'zh-hant', 'en-gb' и т. п. — берём базовый код языка
            suffix = suffixes.get(language.split("-")[0], "")
        if suffix:
            translated = getattr(self, f"{field_name}{suffix}", "")
            if translated:
                return translated
        return getattr(self, field_name, "")


class Season(models.TextChoices):
    ALL_YEAR = "all_year", "Круглый год"
    SUMMER = "summer", "Лето"
    WINTER = "winter", "Зима"
    SPRING_AUTUMN = "spring_autumn", "Весна и осень"


class ObjectStatus(models.TextChoices):
    ACTIVE = "active", "Действующий"
    CONSTRUCTION = "construction", "Строится"
    PLANNED = "planned", "Планируется"
    CLOSED = "closed", "Не действует"


class Village(TranslatedFieldsMixin, models.Model):
    """Населённый пункт округа."""

    slug = models.SlugField("Код", max_length=80, unique=True)
    name = models.CharField("Название", max_length=120)
    name_en = models.CharField("Название (EN)", max_length=120, blank=True)
    name_zh = models.CharField("Название (ZH)", max_length=120, blank=True)
    description = models.TextField("Описание", blank=True)
    description_en = models.TextField("Описание (EN)", blank=True)
    description_zh = models.TextField("Описание (ZH)", blank=True)
    lat = models.FloatField("Широта")
    lng = models.FloatField("Долгота")

    class Meta:
        verbose_name = "Село"
        verbose_name_plural = "Сёла округа"
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def name_i18n(self):
        return self.tr("name")

    @property
    def description_i18n(self):
        return self.tr("description")

    def get_absolute_url(self):
        return reverse("catalog:village_detail", args=[self.slug])


class Category(TranslatedFieldsMixin, models.Model):
    """Категория туристического объекта."""

    slug = models.SlugField("Код", max_length=80, unique=True)
    name = models.CharField("Название", max_length=120)
    name_en = models.CharField("Название (EN)", max_length=120, blank=True)
    name_zh = models.CharField("Название (ZH)", max_length=120, blank=True)
    icon = models.CharField("Значок", max_length=8, blank=True, help_text="Эмодзи для карточек и карты")
    color = models.CharField("Цвет", max_length=7, default="#2e7d32", help_text="HEX, например #2e7d32")
    order = models.PositiveIntegerField("Порядок", default=100)

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    @property
    def name_i18n(self):
        return self.tr("name")


class AttractionQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True)

    def in_district(self):
        return self.filter(in_district=True)

    def with_rating(self):
        """Средняя оценка и число одобренных отзывов одним запросом."""
        return self.annotate(
            rating_avg=Avg("reviews__rating", filter=models.Q(reviews__is_approved=True)),
            rating_count=Count("reviews", filter=models.Q(reviews__is_approved=True)),
        )


class Attraction(TranslatedFieldsMixin, models.Model):
    """Туристический объект."""

    slug = models.SlugField("Код", max_length=100, unique=True)
    title = models.CharField("Название", max_length=200)
    title_en = models.CharField("Название (EN)", max_length=200, blank=True)
    title_zh = models.CharField("Название (ZH)", max_length=200, blank=True)

    category = models.ForeignKey(
        Category,
        verbose_name="Категория",
        on_delete=models.PROTECT,
        related_name="attractions",
    )
    village = models.ForeignKey(
        Village,
        verbose_name="Село",
        on_delete=models.PROTECT,
        related_name="attractions",
        null=True,
        blank=True,
        help_text="Пусто — если объект находится за пределами округа",
    )

    short_description = models.CharField("Краткое описание", max_length=300)
    short_description_en = models.CharField("Краткое описание (EN)", max_length=300, blank=True)
    short_description_zh = models.CharField("Краткое описание (ZH)", max_length=300, blank=True)
    description = models.TextField("Описание", blank=True)
    description_en = models.TextField("Описание (EN)", blank=True)
    description_zh = models.TextField("Описание (ZH)", blank=True)

    fact_note = models.TextField(
        "Примечание о достоверности",
        blank=True,
        help_text="Оговорки о статусе объекта, ограничениях доступа, условности данных",
    )

    lat = models.FloatField("Широта")
    lng = models.FloatField("Долгота")
    address = models.CharField("Адрес", max_length=250, blank=True)

    season = models.CharField("Сезонность", max_length=20, choices=Season.choices, default=Season.ALL_YEAR)
    status = models.CharField("Статус объекта", max_length=20, choices=ObjectStatus.choices, default=ObjectStatus.ACTIVE)
    in_district = models.BooleanField(
        "В границах округа",
        default=True,
        help_text="Снимите отметку для объектов регионального контекста",
    )
    is_fictional = models.BooleanField(
        "Условные данные",
        default=False,
        help_text="Название и услуги придуманы для учебной демонстрации",
    )
    tags = models.CharField("Теги", max_length=250, blank=True, help_text="Через запятую")
    is_published = models.BooleanField("Опубликован", default=True)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Изменён", auto_now=True)

    objects = AttractionQuerySet.as_manager()

    class Meta:
        verbose_name = "Туристический объект"
        verbose_name_plural = "Туристические объекты"
        ordering = ["title"]
        indexes = [
            models.Index(fields=["is_published", "category"]),
            models.Index(fields=["is_published", "village"]),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("catalog:attraction_detail", args=[self.slug])

    @property
    def title_i18n(self):
        return self.tr("title")

    @property
    def short_description_i18n(self):
        return self.tr("short_description")

    @property
    def description_i18n(self):
        return self.tr("description")

    @property
    def tag_list(self):
        return [tag.strip() for tag in self.tags.split(",") if tag.strip()]

    @property
    def cover(self):
        """Обложка: помеченное фото, иначе первое из галереи."""
        photos = list(self.photos.all())
        for photo in photos:
            if photo.is_cover:
                return photo
        return photos[0] if photos else None

    @property
    def is_operating(self):
        return self.status == ObjectStatus.ACTIVE

    def approved_reviews(self):
        return self.reviews.filter(is_approved=True).select_related("user")

    def rating(self):
        """Средняя оценка по одобренным отзывам или None."""
        if hasattr(self, "rating_avg"):
            return self.rating_avg
        return self.reviews.filter(is_approved=True).aggregate(value=Avg("rating"))["value"]


class Photo(models.Model):
    """Фотография объекта."""

    attraction = models.ForeignKey(
        Attraction,
        verbose_name="Объект",
        on_delete=models.CASCADE,
        related_name="photos",
    )
    image = models.ImageField("Изображение", upload_to="attractions/")
    caption = models.CharField("Подпись", max_length=200, blank=True)
    is_cover = models.BooleanField("Обложка", default=False)
    order = models.PositiveIntegerField("Порядок", default=100)

    class Meta:
        verbose_name = "Фотография"
        verbose_name_plural = "Фотографии"
        ordering = ["-is_cover", "order", "id"]

    def __str__(self):
        return f"{self.attraction.title}: {self.caption or self.image.name}"


class Event(TranslatedFieldsMixin, models.Model):
    """Событие календаря."""

    slug = models.SlugField("Код", max_length=100, unique=True)
    title = models.CharField("Название", max_length=200)
    title_en = models.CharField("Название (EN)", max_length=200, blank=True)
    title_zh = models.CharField("Название (ZH)", max_length=200, blank=True)
    description = models.TextField("Описание", blank=True)
    description_en = models.TextField("Описание (EN)", blank=True)
    description_zh = models.TextField("Описание (ZH)", blank=True)
    fact_note = models.TextField("Примечание о достоверности", blank=True)

    date_start = models.DateField("Дата начала")
    date_end = models.DateField("Дата окончания", null=True, blank=True)

    village = models.ForeignKey(
        Village,
        verbose_name="Село",
        on_delete=models.PROTECT,
        related_name="events",
        null=True,
        blank=True,
    )
    attraction = models.ForeignKey(
        Attraction,
        verbose_name="Площадка",
        on_delete=models.SET_NULL,
        related_name="events",
        null=True,
        blank=True,
    )
    is_published = models.BooleanField("Опубликовано", default=True)

    class Meta:
        verbose_name = "Событие"
        verbose_name_plural = "События"
        ordering = ["date_start"]

    def __str__(self):
        return f"{self.title} ({self.date_start:%d.%m.%Y})"

    def get_absolute_url(self):
        return reverse("catalog:event_detail", args=[self.slug])

    @property
    def title_i18n(self):
        return self.tr("title")

    @property
    def description_i18n(self):
        return self.tr("description")

    @property
    def date_finish(self):
        return self.date_end or self.date_start

    @property
    def is_past(self):
        return self.date_finish < timezone.localdate()


class Route(TranslatedFieldsMixin, models.Model):
    """Готовый маршрут."""

    slug = models.SlugField("Код", max_length=100, unique=True)
    title = models.CharField("Название", max_length=200)
    title_en = models.CharField("Название (EN)", max_length=200, blank=True)
    title_zh = models.CharField("Название (ZH)", max_length=200, blank=True)
    description = models.TextField("Описание", blank=True)
    description_en = models.TextField("Описание (EN)", blank=True)
    description_zh = models.TextField("Описание (ZH)", blank=True)

    duration = models.CharField("Длительность", max_length=60, blank=True)
    duration_en = models.CharField("Длительность (EN)", max_length=60, blank=True)
    duration_zh = models.CharField("Длительность (ZH)", max_length=60, blank=True)
    season = models.CharField("Сезон", max_length=20, choices=Season.choices, default=Season.ALL_YEAR)
    difficulty = models.CharField(
        "Сложность",
        max_length=20,
        choices=[("easy", "Лёгкий"), ("medium", "Средний"), ("hard", "Сложный")],
        default="easy",
    )
    cover_image = models.ImageField("Обложка", upload_to="routes/", blank=True)
    is_published = models.BooleanField("Опубликован", default=True)

    class Meta:
        verbose_name = "Маршрут"
        verbose_name_plural = "Маршруты"
        ordering = ["title"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("catalog:route_detail", args=[self.slug])

    @property
    def title_i18n(self):
        return self.tr("title")

    @property
    def description_i18n(self):
        return self.tr("description")

    @property
    def duration_i18n(self):
        return self.tr("duration")


class RoutePoint(models.Model):
    """Точка маршрута — связь «маршрут — объект» с порядком следования."""

    route = models.ForeignKey(Route, verbose_name="Маршрут", on_delete=models.CASCADE, related_name="points")
    attraction = models.ForeignKey(
        Attraction,
        verbose_name="Объект",
        on_delete=models.CASCADE,
        related_name="route_points",
    )
    order = models.PositiveIntegerField("Порядок", default=1)
    note = models.CharField("Комментарий", max_length=250, blank=True)

    class Meta:
        verbose_name = "Точка маршрута"
        verbose_name_plural = "Точки маршрута"
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(fields=["route", "attraction"], name="unique_route_attraction"),
        ]

    def __str__(self):
        return f"{self.order}. {self.attraction.title}"


class Review(models.Model):
    """Отзыв пользователя об объекте. Публикуется после модерации."""

    RATING_CHOICES = [(value, "★" * value) for value in range(1, 6)]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Пользователь",
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    attraction = models.ForeignKey(
        Attraction,
        verbose_name="Объект",
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    rating = models.PositiveSmallIntegerField("Оценка", choices=RATING_CHOICES)
    text = models.TextField("Текст отзыва")
    created_at = models.DateTimeField("Создан", default=timezone.now)
    is_approved = models.BooleanField("Одобрен", default=False)

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "attraction"], name="unique_user_attraction_review"),
        ]

    def __str__(self):
        return f"{self.user} — {self.attraction} ({self.rating})"


class Favorite(models.Model):
    """Объект в избранном пользователя."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Пользователь",
        on_delete=models.CASCADE,
        related_name="favorites",
    )
    attraction = models.ForeignKey(
        Attraction,
        verbose_name="Объект",
        on_delete=models.CASCADE,
        related_name="favorites",
    )
    created_at = models.DateTimeField("Добавлен", auto_now_add=True)

    class Meta:
        verbose_name = "Избранное"
        verbose_name_plural = "Избранное"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "attraction"], name="unique_user_attraction_favorite"),
        ]

    def __str__(self):
        return f"{self.user} ♥ {self.attraction}"
