"""Тесты каталога.

Покрывают сценарии из docs/05-test-cases.md: фильтры каталога, карта,
избранное, отзыв с модерацией, статусы объектов и переключение языка.
"""

import datetime

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Attraction, Category, Event, Favorite, Review, Route, RoutePoint, Village


class BaseContentTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category_rest = Category.objects.create(slug="rest", name="Базы отдыха", icon="🏡", order=10)
        cls.category_border = Category.objects.create(slug="border", name="Приграничье", icon="🌉", order=20)
        cls.village = Village.objects.create(slug="natalyino", name="Натальино", lat=50.44, lng=127.68)
        cls.other_village = Village.objects.create(slug="chigiri", name="Чигири", lat=50.31, lng=127.53)

        cls.base = Attraction.objects.create(
            slug="raduga",
            title="База отдыха «Радуга»",
            category=cls.category_rest,
            village=cls.village,
            short_description="Круглогодичная база на берегу Зеи.",
            lat=50.44,
            lng=127.69,
            season="all_year",
            status="active",
            tags="баня, рыбалка",
        )
        cls.bridge = Attraction.objects.create(
            slug="most",
            title="Мост Благовещенск — Хэйхэ",
            category=cls.category_border,
            village=cls.other_village,
            short_description="Первый автомобильный мост между Россией и Китаем.",
            lat=50.23,
            lng=127.64,
            season="all_year",
            status="active",
        )
        cls.closed = Attraction.objects.create(
            slug="gornolyzhka",
            title="Недостроенная горнолыжная база",
            category=cls.category_rest,
            village=cls.village,
            short_description="Замороженный объект, гостей не принимает.",
            lat=50.45,
            lng=127.70,
            season="winter",
            status="closed",
        )
        cls.outside = Attraction.objects.create(
            slug="muravyovka",
            title="Муравьёвский парк",
            category=cls.category_border,
            village=None,
            short_description="Журавлиный парк в соседнем районе.",
            lat=49.63,
            lng=127.67,
            in_district=False,
        )
        cls.hidden = Attraction.objects.create(
            slug="draft",
            title="Черновик карточки",
            category=cls.category_rest,
            village=cls.village,
            short_description="Не должен быть виден гостю.",
            lat=50.40,
            lng=127.60,
            is_published=False,
        )


class CatalogViewTests(BaseContentTestCase):
    def test_home_page_lists_published_attractions(self):
        response = self.client.get(reverse("catalog:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Радуга")
        self.assertNotContains(response, "Черновик карточки")

    def test_catalog_hides_unpublished(self):
        response = self.client.get(reverse("catalog:attraction_list"))
        slugs = {item.slug for item in response.context["page_obj"]}
        self.assertIn("raduga", slugs)
        self.assertNotIn("draft", slugs)

    def test_catalog_filters_by_category(self):
        response = self.client.get(reverse("catalog:attraction_list"), {"category": "border"})
        slugs = {item.slug for item in response.context["page_obj"]}
        self.assertEqual(slugs, {"most"})

    def test_catalog_filters_by_village_and_season(self):
        response = self.client.get(
            reverse("catalog:attraction_list"), {"village": "natalyino", "season": "winter"}
        )
        slugs = {item.slug for item in response.context["page_obj"]}
        self.assertEqual(slugs, {"gornolyzhka"})

    def test_catalog_search_matches_tags(self):
        response = self.client.get(reverse("catalog:attraction_list"), {"q": "баня"})
        slugs = {item.slug for item in response.context["page_obj"]}
        self.assertEqual(slugs, {"raduga"})

    def test_objects_outside_district_are_separated(self):
        response = self.client.get(reverse("catalog:attraction_list"))
        main_slugs = {item.slug for item in response.context["page_obj"]}
        outside_slugs = {item.slug for item in response.context["outside"]}
        self.assertNotIn("muravyovka", main_slugs)
        self.assertEqual(outside_slugs, {"muravyovka"})

    def test_closed_object_shows_warning(self):
        response = self.client.get(self.closed.get_absolute_url())
        self.assertContains(response, "Объект не действует")

    def test_map_json_returns_published_only(self):
        response = self.client.get(reverse("catalog:attractions_json"))
        payload = response.json()
        slugs = {item["slug"] for item in payload["items"]}
        self.assertNotIn("draft", slugs)
        self.assertIn("raduga", slugs)
        self.assertEqual(payload["count"], len(payload["items"]))

    def test_village_page_lists_its_attractions(self):
        response = self.client.get(self.village.get_absolute_url())
        slugs = {item.slug for item in response.context["attractions"]}
        self.assertEqual(slugs, {"raduga", "gornolyzhka"})


class EventTests(BaseContentTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        today = timezone.localdate()
        cls.upcoming = Event.objects.create(
            slug="fair",
            title="Ярмарка",
            date_start=today + datetime.timedelta(days=10),
            village=cls.village,
        )
        cls.past = Event.objects.create(
            slug="old",
            title="Прошедший праздник",
            date_start=today - datetime.timedelta(days=30),
            village=cls.village,
        )

    def test_calendar_shows_upcoming_by_default(self):
        response = self.client.get(reverse("catalog:event_list"))
        slugs = {event.slug for event in response.context["events"]}
        self.assertEqual(slugs, {"fair"})

    def test_calendar_can_show_past(self):
        response = self.client.get(reverse("catalog:event_list"), {"past": "1"})
        slugs = {event.slug for event in response.context["events"]}
        self.assertEqual(slugs, {"old"})

    def test_calendar_filters_by_month(self):
        month = self.upcoming.date_start.month
        response = self.client.get(reverse("catalog:event_list"), {"month": str(month)})
        self.assertIn(self.upcoming, list(response.context["events"]))


class RouteTests(BaseContentTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.route = Route.objects.create(slug="border-weekend", title="Приграничный уик-энд", duration="2 дня")
        RoutePoint.objects.create(route=cls.route, attraction=cls.bridge, order=1)
        RoutePoint.objects.create(route=cls.route, attraction=cls.base, order=2)

    def test_route_detail_lists_points_in_order(self):
        response = self.client.get(self.route.get_absolute_url())
        titles = [point.attraction.slug for point in response.context["points"]]
        self.assertEqual(titles, ["most", "raduga"])

    def test_route_points_json_is_prepared_for_map(self):
        response = self.client.get(self.route.get_absolute_url())
        points = response.context["points_json"]
        self.assertEqual(len(points), 2)
        self.assertIn("lat", points[0])
        self.assertIn("url", points[0])

    def test_attraction_page_shows_related_routes(self):
        response = self.client.get(self.bridge.get_absolute_url())
        self.assertIn(self.route, list(response.context["routes"]))


class FavoriteTests(BaseContentTestCase):
    def setUp(self):
        self.user = User.objects.create_user("tourist", password="test-pass-12345")

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.post(reverse("catalog:toggle_favorite", args=[self.base.slug]))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_toggle_adds_and_removes(self):
        self.client.login(username="tourist", password="test-pass-12345")
        url = reverse("catalog:toggle_favorite", args=[self.base.slug])

        self.client.post(url)
        self.assertTrue(Favorite.objects.filter(user=self.user, attraction=self.base).exists())

        self.client.post(url)
        self.assertFalse(Favorite.objects.filter(user=self.user, attraction=self.base).exists())

    def test_get_request_is_not_allowed(self):
        self.client.login(username="tourist", password="test-pass-12345")
        response = self.client.get(reverse("catalog:toggle_favorite", args=[self.base.slug]))
        self.assertEqual(response.status_code, 405)


class ReviewModerationTests(BaseContentTestCase):
    def setUp(self):
        self.user = User.objects.create_user("tourist", password="test-pass-12345")

    def test_new_review_waits_for_moderation(self):
        self.client.login(username="tourist", password="test-pass-12345")
        response = self.client.post(
            self.base.get_absolute_url(),
            {"rating": 5, "text": "Хорошее место, приезжали всей семьёй на выходные."},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        review = Review.objects.get(user=self.user, attraction=self.base)
        self.assertFalse(review.is_approved)
        self.assertNotContains(response, "приезжали всей семьёй")

    def test_approved_review_is_visible_and_counted(self):
        Review.objects.create(
            user=self.user,
            attraction=self.base,
            rating=4,
            text="Тёплые домики, хорошая баня, рекомендуем зимой.",
            is_approved=True,
        )
        response = self.client.get(self.base.get_absolute_url())
        self.assertContains(response, "Тёплые домики")
        self.assertAlmostEqual(response.context["attraction"].rating_avg, 4.0)

    def test_short_review_is_rejected(self):
        self.client.login(username="tourist", password="test-pass-12345")
        self.client.post(self.base.get_absolute_url(), {"rating": 5, "text": "Класс"})
        self.assertFalse(Review.objects.filter(attraction=self.base).exists())

    def test_second_review_is_not_created(self):
        self.client.login(username="tourist", password="test-pass-12345")
        payload = {"rating": 5, "text": "Первый отзыв об этом месте, всё понравилось."}
        self.client.post(self.base.get_absolute_url(), payload)
        self.client.post(self.base.get_absolute_url(), {"rating": 1, "text": "Второй отзыв, так делать нельзя."})
        self.assertEqual(Review.objects.filter(user=self.user, attraction=self.base).count(), 1)


class TranslationTests(BaseContentTestCase):
    def test_object_falls_back_to_russian_without_translation(self):
        self.base.title_en = ""
        self.assertEqual(self.base.title_i18n, "База отдыха «Радуга»")

    def test_english_title_is_used_when_language_switched(self):
        self.base.title_en = "Raduga recreation centre"
        self.base.save()
        self.client.post(reverse("set_language"), {"language": "en", "next": "/"})
        response = self.client.get(self.base.get_absolute_url())
        self.assertContains(response, "Raduga recreation centre")

    def test_interface_language_switches(self):
        response = self.client.post(reverse("set_language"), {"language": "en", "next": "/"}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Catalogue")
