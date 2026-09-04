from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse


class RegistrationTests(TestCase):
    def test_registration_creates_user_and_logs_in(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "novikova",
                "first_name": "Дарья",
                "last_name": "Новикова",
                "email": "novikova@example.org",
                "password1": "TouristAmur2026",
                "password2": "TouristAmur2026",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username="novikova").exists())
        self.assertEqual(int(self.client.session["_auth_user_id"]), User.objects.get(username="novikova").pk)

    def test_duplicate_email_is_rejected(self):
        User.objects.create_user("first", email="same@example.org", password="TouristAmur2026")
        self.client.post(
            reverse("accounts:register"),
            {
                "username": "second",
                "first_name": "Иван",
                "last_name": "Иванов",
                "email": "same@example.org",
                "password1": "TouristAmur2026",
                "password2": "TouristAmur2026",
            },
        )
        self.assertFalse(User.objects.filter(username="second").exists())


class ProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("tourist", password="TouristAmur2026")

    def test_profile_requires_login(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_profile_can_be_updated(self):
        self.client.login(username="tourist", password="TouristAmur2026")
        self.client.post(
            reverse("accounts:profile"),
            {"first_name": "Мария", "last_name": "Иванова", "email": "maria@example.org"},
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Мария")
        self.assertEqual(self.user.email, "maria@example.org")

    def test_favorites_page_requires_login(self):
        response = self.client.get(reverse("accounts:favorites"))
        self.assertEqual(response.status_code, 302)


class AdminAccessTests(TestCase):
    def _content_manager(self):
        """Менеджер с правами на контент — так же, как их выдаёт seed_demo."""
        user = User.objects.create_user("manager", password="TouristAmur2026", is_staff=True)
        group = Group.objects.create(name="Контент-менеджеры")
        group.permissions.set(
            Permission.objects.filter(content_type__in=ContentType.objects.filter(app_label="catalog"))
        )
        user.groups.add(group)
        return user

    def test_content_manager_can_open_admin(self):
        self._content_manager()
        self.client.login(username="manager", password="TouristAmur2026")
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)

    def test_content_manager_can_manage_content(self):
        """Отметки is_staff мало: без прав на модели разделы недоступны."""
        self._content_manager()
        self.client.login(username="manager", password="TouristAmur2026")
        for url in (
            "/admin/catalog/attraction/",
            "/admin/catalog/review/",
            "/admin/catalog/route/",
            "/admin/catalog/event/",
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_content_manager_cannot_manage_users(self):
        self._content_manager()
        self.client.login(username="manager", password="TouristAmur2026")
        self.assertEqual(self.client.get("/admin/auth/user/").status_code, 403)

    def test_regular_user_cannot_open_admin(self):
        User.objects.create_user("tourist", password="TouristAmur2026")
        self.client.login(username="tourist", password="TouristAmur2026")
        response = self.client.get("/admin/", follow=True)
        self.assertContains(response, "Войти", status_code=200)
