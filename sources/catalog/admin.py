"""Панель контент-менеджера на базе стандартной админки Django."""

from django.contrib import admin, messages
from django.utils.html import format_html

from .models import (
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


class PhotoInline(admin.TabularInline):
    model = Photo
    extra = 1
    fields = ("image", "caption", "is_cover", "order")


class RoutePointInline(admin.TabularInline):
    model = RoutePoint
    extra = 1
    fields = ("order", "attraction", "note")
    autocomplete_fields = ("attraction",)
    ordering = ("order",)


@admin.register(Village)
class VillageAdmin(admin.ModelAdmin):
    list_display = ("name", "name_en", "name_zh", "lat", "lng", "attractions_count")
    search_fields = ("name", "name_en", "name_zh", "slug")
    prepopulated_fields = {"slug": ("name",)}
    fieldsets = (
        (None, {"fields": ("slug", "name", "lat", "lng")}),
        ("Переводы", {"fields": ("name_en", "name_zh"), "classes": ("collapse",)}),
        ("Описание", {"fields": ("description", "description_en", "description_zh")}),
    )

    @admin.display(description="Объектов")
    def attractions_count(self, obj):
        return obj.attractions.count()


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("icon", "name", "name_en", "name_zh", "color_box", "order")
    list_editable = ("order",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(description="Цвет")
    def color_box(self, obj):
        return format_html(
            '<span style="display:inline-block;width:2.5rem;height:1rem;'
            'background:{};border:1px solid #999;"></span> {}',
            obj.color,
            obj.color,
        )


@admin.register(Attraction)
class AttractionAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "village", "season", "status", "in_district", "is_published")
    list_filter = ("category", "village", "season", "status", "in_district", "is_published", "is_fictional")
    search_fields = ("title", "title_en", "title_zh", "short_description", "description", "tags")
    prepopulated_fields = {"slug": ("title",)}
    list_editable = ("is_published",)
    inlines = [PhotoInline]
    date_hierarchy = "created_at"
    actions = ["publish", "unpublish"]
    fieldsets = (
        (None, {"fields": ("slug", "title", "category", "village", "is_published")}),
        ("Переводы названия", {"fields": ("title_en", "title_zh"), "classes": ("collapse",)}),
        (
            "Описание",
            {
                "fields": (
                    "short_description",
                    "short_description_en",
                    "short_description_zh",
                    "description",
                    "description_en",
                    "description_zh",
                )
            },
        ),
        ("Расположение", {"fields": ("lat", "lng", "address", "in_district")}),
        ("Статус и признаки", {"fields": ("season", "status", "is_fictional", "tags", "fact_note")}),
    )

    @admin.action(description="Опубликовать выбранные объекты")
    def publish(self, request, queryset):
        updated = queryset.update(is_published=True)
        self.message_user(request, f"Опубликовано объектов: {updated}", messages.SUCCESS)

    @admin.action(description="Снять с публикации")
    def unpublish(self, request, queryset):
        updated = queryset.update(is_published=False)
        self.message_user(request, f"Снято с публикации: {updated}", messages.SUCCESS)


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ("attraction", "caption", "is_cover", "order")
    list_filter = ("is_cover", "attraction__category")
    search_fields = ("attraction__title", "caption")


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "date_start", "date_end", "village", "attraction", "is_published")
    list_filter = ("is_published", "village", "date_start")
    search_fields = ("title", "title_en", "title_zh", "description")
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "date_start"
    autocomplete_fields = ("attraction",)
    fieldsets = (
        (None, {"fields": ("slug", "title", "date_start", "date_end", "village", "attraction", "is_published")}),
        ("Переводы названия", {"fields": ("title_en", "title_zh"), "classes": ("collapse",)}),
        ("Описание", {"fields": ("description", "description_en", "description_zh", "fact_note")}),
    )


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ("title", "duration", "season", "difficulty", "points_count", "is_published")
    list_filter = ("season", "difficulty", "is_published")
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [RoutePointInline]
    fieldsets = (
        (None, {"fields": ("slug", "title", "duration", "season", "difficulty", "cover_image", "is_published")}),
        ("Переводы", {"fields": ("title_en", "title_zh", "duration_en", "duration_zh"), "classes": ("collapse",)}),
        ("Описание", {"fields": ("description", "description_en", "description_zh")}),
    )

    @admin.display(description="Точек")
    def points_count(self, obj):
        return obj.points.count()


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """Модерация отзывов: новые приходят с is_approved = False."""

    list_display = ("attraction", "user", "rating", "short_text", "created_at", "is_approved")
    list_filter = ("is_approved", "rating", "created_at", "attraction__category")
    search_fields = ("text", "user__username", "attraction__title")
    list_editable = ("is_approved",)
    actions = ["approve", "reject"]
    autocomplete_fields = ("attraction",)

    @admin.display(description="Отзыв")
    def short_text(self, obj):
        return obj.text[:60] + ("…" if len(obj.text) > 60 else "")

    @admin.action(description="Одобрить и опубликовать")
    def approve(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f"Одобрено отзывов: {updated}", messages.SUCCESS)

    @admin.action(description="Снять с публикации")
    def reject(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f"Снято с публикации отзывов: {updated}", messages.WARNING)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "attraction", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "attraction__title")
