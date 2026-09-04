"""Представления портала."""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, F, Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from .forms import AttractionFilterForm, ReviewForm
from .models import (
    Attraction,
    Category,
    Event,
    Favorite,
    ObjectStatus,
    Review,
    Route,
    Season,
    Village,
)

PORTAL = settings.PORTAL

# Ключ сортировки -> (выражение для order_by, подпись в форме фильтра)
SORT_OPTIONS = {
    "title": (F("title").asc(), _("По названию")),
    "rating": (F("rating_avg").desc(nulls_last=True), _("По рейтингу")),
    "new": (F("created_at").desc(), _("Сначала новые")),
}


def _published_attractions():
    return (
        Attraction.objects.published()
        .select_related("category", "village")
        .prefetch_related("photos")
        .with_rating()
    )


def _favorite_slugs(request):
    """Коды объектов в избранном текущего пользователя."""
    if not request.user.is_authenticated:
        return set()
    return set(Favorite.objects.filter(user=request.user).values_list("attraction__slug", flat=True))


def home(request):
    today = timezone.localdate()
    attractions = _published_attractions()

    context = {
        "featured": attractions.in_district().filter(status=ObjectStatus.ACTIVE).order_by("-rating_avg", "title")[:6],
        # order_by нужен явно: annotate() с агрегатом по связанной модели
        # сбрасывает сортировку из Meta, и категории уходили по алфавиту кода.
        "categories": Category.objects.annotate(count=Count("attractions", filter=Q(attractions__is_published=True)))
        .filter(count__gt=0)
        .order_by("order", "name"),
        "events": Event.objects.filter(is_published=True)
        .filter(Q(date_end__gte=today) | Q(date_start__gte=today))
        .select_related("village", "attraction")[:4],
        "routes": Route.objects.filter(is_published=True).prefetch_related("points__attraction")[:3],
        "stats": {
            "attractions": attractions.in_district().count(),
            "villages": Village.objects.count(),
            "routes": Route.objects.filter(is_published=True).count(),
            "events": Event.objects.filter(is_published=True).count(),
        },
        "favorite_slugs": _favorite_slugs(request),
    }
    return render(request, "catalog/home.html", context)


def attraction_list(request):
    queryset = _published_attractions()

    form = AttractionFilterForm(
        request.GET or None,
        categories=[(c.slug, f"{c.icon} {c.name_i18n}".strip()) for c in Category.objects.all()],
        villages=[(v.slug, v.name_i18n) for v in Village.objects.all()],
        seasons=Season.choices,
        sort_choices=[(key, label) for key, (_field, label) in SORT_OPTIONS.items()],
    )

    filters = {}
    if form.is_valid():
        filters = {key: value for key, value in form.cleaned_data.items() if value}

    if query := filters.get("q"):
        queryset = queryset.filter(
            Q(title__icontains=query)
            | Q(title_en__icontains=query)
            | Q(title_zh__icontains=query)
            | Q(short_description__icontains=query)
            | Q(description__icontains=query)
            | Q(tags__icontains=query)
        )
    if category := filters.get("category"):
        queryset = queryset.filter(category__slug=category)
    if village := filters.get("village"):
        queryset = queryset.filter(village__slug=village)
    if season := filters.get("season"):
        queryset = queryset.filter(season=season)

    sort_key = filters.get("sort") or "title"
    order_expression = SORT_OPTIONS.get(sort_key, SORT_OPTIONS["title"])[0]
    queryset = queryset.order_by(order_expression, "title")

    # Объекты вне округа показываем отдельным блоком, чтобы не путать
    # их с предложением самого округа.
    outside = queryset.filter(in_district=False)
    queryset = queryset.filter(in_district=True)

    # В статической витрине страниц нет: адрес с ?page= там не обрабатывается,
    # поэтому выводим весь каталог одной страницей.
    per_page = 1000 if settings.STATIC_DEMO else PORTAL["items_per_page"]
    paginator = Paginator(queryset, per_page)
    page = paginator.get_page(request.GET.get("page"))

    querystring = request.GET.copy()
    querystring.pop("page", None)

    context = {
        "form": form,
        "page_obj": page,
        "total": paginator.count,
        "outside": outside,
        "querystring": querystring.urlencode(),
        "has_filters": bool({k: v for k, v in filters.items() if k != "sort"}),
        "favorite_slugs": _favorite_slugs(request),
    }
    return render(request, "catalog/attraction_list.html", context)


def attraction_detail(request, slug):
    attraction = get_object_or_404(
        _published_attractions(),
        slug=slug,
    )
    reviews = attraction.approved_reviews()
    user_review = None
    form = None

    if request.user.is_authenticated:
        user_review = Review.objects.filter(user=request.user, attraction=attraction).first()
        if request.method == "POST":
            if user_review:
                messages.info(request, _("Вы уже оставляли отзыв об этом объекте."))
                return redirect(attraction)
            form = ReviewForm(request.POST)
            if form.is_valid():
                review = form.save(commit=False)
                review.user = request.user
                review.attraction = attraction
                review.is_approved = False
                review.save()
                messages.success(
                    request,
                    _("Спасибо! Отзыв отправлен на модерацию и появится на странице после проверки."),
                )
                return redirect(attraction)
        elif not user_review:
            form = ReviewForm()

    context = {
        "attraction": attraction,
        "photos": attraction.photos.all(),
        "reviews": reviews,
        "form": form,
        "user_review": user_review,
        "is_favorite": attraction.slug in _favorite_slugs(request),
        "routes": Route.objects.filter(is_published=True, points__attraction=attraction).distinct(),
        "events": attraction.events.filter(is_published=True, date_start__gte=timezone.localdate()),
        "nearby": (
            _published_attractions()
            .filter(village=attraction.village)
            .exclude(pk=attraction.pk)[:3]
            if attraction.village
            else Attraction.objects.none()
        ),
    }
    return render(request, "catalog/attraction_detail.html", context)


def map_page(request):
    context = {
        "categories": Category.objects.all(),
        # Через json_script: при русской локали числа в шаблоне выводятся
        # с запятой в качестве разделителя и ломают Leaflet.
        "map_config": {"center": PORTAL["map_center"], "zoom": PORTAL["map_zoom"]},
    }
    return render(request, "catalog/map.html", context)


def attractions_geojson(request):
    """Данные для карты: все опубликованные объекты с координатами."""
    queryset = Attraction.objects.published().select_related("category", "village")

    if category := request.GET.get("category"):
        queryset = queryset.filter(category__slug=category)
    if route_slug := request.GET.get("route"):
        queryset = queryset.filter(route_points__route__slug=route_slug).order_by("route_points__order")

    features = [
        {
            "slug": item.slug,
            "title": item.title_i18n,
            "short": item.short_description_i18n,
            "lat": item.lat,
            "lng": item.lng,
            "url": item.get_absolute_url(),
            "category": item.category.slug,
            "category_name": item.category.name_i18n,
            "icon": item.category.icon,
            "color": item.category.color,
            "village": item.village.name_i18n if item.village else "",
            "status": item.status,
            "status_label": item.get_status_display(),
            "in_district": item.in_district,
        }
        for item in queryset
    ]
    return JsonResponse({"count": len(features), "items": features})


def event_list(request):
    today = timezone.localdate()
    queryset = Event.objects.filter(is_published=True).select_related("village", "attraction")

    show_past = request.GET.get("past") == "1"
    if show_past:
        queryset = queryset.filter(date_start__lt=today).order_by("-date_start")
    else:
        queryset = queryset.filter(Q(date_end__gte=today) | Q(date_start__gte=today)).order_by("date_start")

    month = request.GET.get("month")
    if month and month.isdigit() and 1 <= int(month) <= 12:
        queryset = queryset.filter(date_start__month=int(month))

    village = request.GET.get("village")
    if village:
        queryset = queryset.filter(village__slug=village)

    months = [
        (str(number), name)
        for number, name in enumerate(
            [
                _("Январь"), _("Февраль"), _("Март"), _("Апрель"), _("Май"), _("Июнь"),
                _("Июль"), _("Август"), _("Сентябрь"), _("Октябрь"), _("Ноябрь"), _("Декабрь"),
            ],
            start=1,
        )
    ]

    context = {
        "events": queryset,
        "months": months,
        "villages": Village.objects.all(),
        "selected_month": month or "",
        "selected_village": village or "",
        "show_past": show_past,
    }
    return render(request, "catalog/event_list.html", context)


def event_detail(request, slug):
    event = get_object_or_404(
        Event.objects.filter(is_published=True).select_related("village", "attraction"),
        slug=slug,
    )
    return render(request, "catalog/event_detail.html", {"event": event})


def route_list(request):
    routes = (
        Route.objects.filter(is_published=True)
        .prefetch_related(Prefetch("points__attraction", queryset=Attraction.objects.select_related("village")))
        .annotate(points_total=Count("points"))
    )
    season = request.GET.get("season")
    if season:
        routes = routes.filter(season=season)
    context = {
        "routes": routes,
        "seasons": Season.choices,
        "selected_season": season or "",
    }
    return render(request, "catalog/route_list.html", context)


def route_detail(request, slug):
    route = get_object_or_404(Route.objects.filter(is_published=True), slug=slug)
    points = route.points.select_related("attraction__category", "attraction__village").prefetch_related(
        "attraction__photos"
    )
    context = {
        "route": route,
        "points": points,
        "map_config": {"center": PORTAL["map_center"], "zoom": PORTAL["map_zoom"]},
        "points_json": [
            {
                "title": point.attraction.title_i18n,
                "lat": point.attraction.lat,
                "lng": point.attraction.lng,
                "url": point.attraction.get_absolute_url(),
                "color": point.attraction.category.color,
            }
            for point in points
        ],
        "favorite_slugs": _favorite_slugs(request),
    }
    return render(request, "catalog/route_detail.html", context)


def village_detail(request, slug):
    village = get_object_or_404(Village, slug=slug)
    context = {
        "village": village,
        "attractions": _published_attractions().filter(village=village),
        "events": village.events.filter(is_published=True, date_start__gte=timezone.localdate()),
        "favorite_slugs": _favorite_slugs(request),
    }
    return render(request, "catalog/village_detail.html", context)


@login_required
@require_POST
def toggle_favorite(request, slug):
    attraction = get_object_or_404(Attraction.objects.published(), slug=slug)
    favorite = Favorite.objects.filter(user=request.user, attraction=attraction).first()
    if favorite:
        favorite.delete()
        messages.info(request, _("Объект убран из избранного."))
    else:
        Favorite.objects.create(user=request.user, attraction=attraction)
        messages.success(request, _("Объект добавлен в избранное."))
    return redirect(request.POST.get("next") or attraction.get_absolute_url())


def about(request):
    return render(request, "pages/about.html")


def how_to_get(request):
    return render(request, "pages/how_to_get.html", {"villages": Village.objects.all()})


def contacts(request):
    return render(request, "pages/contacts.html")
