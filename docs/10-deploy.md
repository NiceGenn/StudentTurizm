# Публикация портала в интернете

## Два способа опубликовать

| | Витрина на GitHub Pages | Полная версия на хостинге |
|---|---|---|
| Ссылка | `логин.github.io/StudentTurizm` | например `имя.pythonanywhere.com` |
| Настройка | одно переключение в настройках репозитория | около 15 минут |
| Каталог, фильтры, поиск | работают (в браузере) | работают |
| Карта, маршруты, события | работают | работают |
| Три языка | работают | работают |
| Вход, избранное, отзывы | **нет** | работают |
| Панель управления | **нет** | работает |
| Обновление | само при каждом `git push` | вручную |

## Витрина на GitHub Pages

GitHub Pages отдаёт только готовые файлы и не выполняет Python, поэтому сам
Django там работать не может. Но публичную часть портала можно заранее
собрать в обычные HTML-страницы — это и делает `tools/build_static.py`:
обходит каталог, карточки, карту, маршруты, события и справочные страницы
на трёх языках и сохраняет их как файлы.

Чтобы фильтры каталога не сломались (статический хостинг игнорирует
условия в адресе запроса), в этом режиме та же выборка выполняется в
браузере — по данным, которые уже лежат в карточках.

Регистрация, избранное, отзывы и панель управления в витрину не попадают:
им нужен работающий сервер. В шапке витрины стоит предупреждение об этом.

**Как включить:** в репозитории **Settings → Pages → Build and deployment →
Source** выберите **GitHub Actions** (вместо «Deploy from a branch») и
сохраните. Дальше всё делает workflow `.github/workflows/pages.yml`: при
каждом `git push` в `main` он собирает витрину заново и публикует.

Ход сборки виден на вкладке **Actions**, готовый адрес — там же в шаге
«Публикация» и в Settings → Pages.

**Собрать витрину локально и посмотреть:**

```bash
python tools/build_static.py
cd build && python -m http.server 8080
```

Откроется по адресу `http://127.0.0.1:8080/` — правда, ссылки внутри
рассчитаны на подпапку `/StudentTurizm`, поэтому для полной проверки
положите папку `build` внутрь каталога с этим именем.

## Полная версия: почему нужен отдельный хостинг

На каждый запрос портал выполняет код на Python: фильтрует каталог, считает
рейтинг, проверяет пароль, сохраняет отзыв. Для этого нужен хостинг, где
работает Python-процесс.

## Что нужно поменять перед публикацией

Код менять не придётся — всё настраивается переменными окружения.

| Переменная | Значение для публикации |
|---|---|
| `DJANGO_DEBUG` | `False` |
| `DJANGO_SECRET_KEY` | свой случайный ключ (см. ниже) |
| `DJANGO_ALLOWED_HOSTS` | ваш домен, например `student.pythonanywhere.com` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://ваш-домен` |

Сгенерировать ключ:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Кроме этого:

1. **Смените учебные пароли.** `admin12345` и остальные лежат в открытом
   виде в `data/demo_users.json`, то есть известны каждому, кто видел
   репозиторий. Создайте своего администратора
   (`python sources/manage.py createsuperuser`) и удалите демонстрационные
   учётные записи или задайте им новые пароли.
2. **Соберите статику:** `python sources/manage.py collectstatic --noinput`.
   Раздачей займётся WhiteNoise — он уже поддержан в настройках и
   подключается сам, если установлен (`pip install whitenoise`).
3. **Замените условные карточки.** Пять объектов помечены «Учебные данные»
   (список — в [08-facts.md](08-facts.md)). На публичном сайте про реальные
   сёла выдуманные базы отдыха вводят людей в заблуждение: либо поставьте
   реальные данные, либо снимите эти карточки с публикации.
4. **Оставьте дисклеймер** об учебном характере проекта на странице «О
   портале» и в подвале.
5. **PostgreSQL вместо SQLite** — желательно, если сайт живёт долго и им
   пользуются несколько человек одновременно (`DB_ENGINE=postgres`).

## PythonAnywhere — самый короткий путь

Бесплатный тариф, сделан под Django, всё настраивается через веб-интерфейс.
Адрес будет вида `имя.pythonanywhere.com`.

1. Зарегистрируйтесь на <https://www.pythonanywhere.com> (тариф Beginner —
   бесплатный, карта не нужна).
2. Откройте вкладку **Consoles** → **Bash** и выполните:

   ```bash
   git clone https://github.com/NiceGenn/StudentTurizm.git
   cd StudentTurizm
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install -r sources/requirements.txt
   python sources/manage.py migrate
   python sources/manage.py seed_demo
   python sources/manage.py collectstatic --noinput
   python sources/manage.py createsuperuser
   ```

3. Вкладка **Web** → **Add a new web app** → **Manual configuration** →
   **Python 3.11**.
4. В разделе **Code** укажите:
   - Source code: `/home/ИМЯ/StudentTurizm/sources`
   - Working directory: `/home/ИМЯ/StudentTurizm`
   - Virtualenv: `/home/ИМЯ/StudentTurizm/.venv`
5. Нажмите на файл **WSGI configuration file** и замените его содержимое:

   ```python
   import os
   import sys

   path = "/home/ИМЯ/StudentTurizm/sources"
   if path not in sys.path:
       sys.path.insert(0, path)

   os.environ["DJANGO_SETTINGS_MODULE"] = "portal.settings"
   os.environ["DJANGO_DEBUG"] = "False"
   os.environ["DJANGO_SECRET_KEY"] = "вставьте сюда свой ключ"
   os.environ["DJANGO_ALLOWED_HOSTS"] = "ИМЯ.pythonanywhere.com"
   os.environ["DJANGO_CSRF_TRUSTED_ORIGINS"] = "https://ИМЯ.pythonanywhere.com"

   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```

6. В разделе **Static files** добавьте:
   - URL `/static/` → Directory `/home/ИМЯ/StudentTurizm/sources/staticfiles`
   - URL `/media/` → Directory `/home/ИМЯ/StudentTurizm/sources/media`
7. Нажмите зелёную кнопку **Reload**. Сайт открыт по адресу
   `https://ИМЯ.pythonanywhere.com`.

Замените `ИМЯ` на своё имя пользователя во всех путях.

**Что помнить про бесплатный тариф:** сайт нужно продлевать нажатием кнопки
раз в три месяца (приходит письмо-напоминание), база — SQLite, исходящие
запросы в интернет ограничены белым списком. Для учебного проекта этого
достаточно: тайлы карты приходят в браузер посетителя напрямую с серверов
OpenStreetMap, а не через ваш сервер.

## Обновление сайта после правок

```bash
cd ~/StudentTurizm
git pull
source .venv/bin/activate
python sources/manage.py migrate
python sources/manage.py collectstatic --noinput
```

Затем **Reload** на вкладке Web.

## Альтернативы

| Где | Плюсы | Минусы |
|---|---|---|
| **Render.com** | автодеплой прямо из GitHub: запушили — обновилось | на бесплатном тарифе сайт засыпает после 15 минут простоя, первый заход потом ждёт около минуты |
| **Timeweb Cloud, Amvera, Reg.ru** | российские, платят рублями, есть PostgreSQL | платно, от нескольких сотен рублей в месяц |
| **ngrok** | временная публичная ссылка на сайт, запущенный у вас на компьютере: `ngrok http 8000` | ссылка живёт, пока включён компьютер; для показа комиссии удалённо — годится, как постоянный сайт — нет |

Для ngrok не забудьте добавить выданный домен в `DJANGO_ALLOWED_HOSTS` и
`DJANGO_CSRF_TRUSTED_ORIGINS`.
