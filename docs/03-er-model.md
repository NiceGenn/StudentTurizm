# ER-модель базы данных

```mermaid
erDiagram
    VILLAGE ||--o{ ATTRACTION : "расположен в"
    CATEGORY ||--o{ ATTRACTION : "относится к"
    ATTRACTION ||--o{ PHOTO : "имеет"
    ATTRACTION ||--o{ REVIEW : "получает"
    ATTRACTION ||--o{ FAVORITE : "сохраняется в"
    ATTRACTION ||--o{ ROUTEPOINT : "входит в"
    ROUTE ||--o{ ROUTEPOINT : "состоит из"
    VILLAGE ||--o{ EVENT : "проходит в"
    ATTRACTION ||--o{ EVENT : "площадка"
    USER ||--o{ REVIEW : "пишет"
    USER ||--o{ FAVORITE : "добавляет"

    VILLAGE {
        int id PK
        string slug UK
        string name
        string name_en
        string name_zh
        text description
        text description_en
        text description_zh
        float lat
        float lng
    }

    CATEGORY {
        int id PK
        string slug UK
        string name
        string name_en
        string name_zh
        string icon
        string color
        int order
    }

    ATTRACTION {
        int id PK
        string slug UK
        string title
        string title_en
        string title_zh
        int category_id FK
        int village_id FK "NULL для объектов вне округа"
        string short_description
        text description
        text fact_note
        float lat
        float lng
        string address
        string season "all_year|summer|winter|spring_autumn"
        string status "active|construction|planned|closed"
        bool in_district
        bool is_fictional
        string tags
        bool is_published
        datetime created_at
        datetime updated_at
    }

    PHOTO {
        int id PK
        int attraction_id FK
        image image
        string caption
        bool is_cover
        int order
    }

    EVENT {
        int id PK
        string slug UK
        string title
        text description
        text fact_note
        date date_start
        date date_end "NULL для однодневных"
        int village_id FK
        int attraction_id FK "NULL"
        bool is_published
    }

    ROUTE {
        int id PK
        string slug UK
        string title
        text description
        string duration
        string season
        string difficulty "easy|medium|hard"
        image cover_image
        bool is_published
    }

    ROUTEPOINT {
        int id PK
        int route_id FK
        int attraction_id FK
        int order
        string note
    }

    USER {
        int id PK
        string username UK
        string first_name
        string last_name
        string email
        string password "хеш"
        bool is_staff
        bool is_superuser
    }

    REVIEW {
        int id PK
        int user_id FK
        int attraction_id FK
        int rating "1..5"
        text text
        datetime created_at
        bool is_approved
    }

    FAVORITE {
        int id PK
        int user_id FK
        int attraction_id FK
        datetime created_at
    }
```

## Пояснения к модели

### Многоязычность

Переводимые поля продублированы суффиксами `_en` и `_zh`. Это самый простой
для чтения вариант: одна запись — все языки, никаких дополнительных таблиц и
JOIN-ов. Метод `TranslatedFieldsMixin.tr()` выбирает версию по активному
языку и откатывается на русскую, если перевод пуст, поэтому страница никогда
не оказывается пустой.

Альтернатива для ВКР — библиотека `django-modeltranslation` или отдельная
таблица переводов; на текущем объёме они себя не окупают.

### Связь «многие-ко-многим» с порядком

`Route` и `Attraction` связаны через `RoutePoint`. Промежуточная таблица
нужна не только ради связи, но и ради двух собственных полей: `order`
(порядок следования, по нему рисуется линия на карте) и `note` (комментарий
именно для этой точки в этом маршруте).

### Ограничения целостности

| Ограничение | Смысл |
|---|---|
| `unique_route_attraction` (route, attraction) | объект не может входить в один маршрут дважды |
| `unique_user_attraction_review` (user, attraction) | один пользователь — один отзыв об объекте |
| `unique_user_attraction_favorite` (user, attraction) | объект добавляется в избранное один раз |
| `Attraction.category` → `PROTECT` | категорию с объектами нельзя удалить случайно |
| `Attraction.village` → `PROTECT` | то же для села |
| `Photo.attraction` → `CASCADE` | фотографии живут только вместе с объектом |
| `Event.attraction` → `SET_NULL` | удаление площадки не удаляет само событие |

### Индексы

Составные индексы `(is_published, category)` и `(is_published, village)`
покрывают основные запросы каталога: публичные представления всегда
фильтруют по `is_published`, а затем по категории или селу.

### Отступление от исходного ТЗ

`Attraction.village` допускает `NULL`. Это понадобилось для объектов
регионального контекста — трансграничной канатной дороги (она в самом
Благовещенске) и Муравьёвского парка (Тамбовский район). Такие записи
помечаются `in_district = false`, выводятся отдельным блоком и не попадают
в маршруты округа; валидатор `tools/check_data.py` следит за тем, чтобы
объект без села обязательно имел `in_district = false`.

### Рейтинг

Рейтинг не хранится в таблице, а считается запросом
`Avg("reviews__rating", filter=Q(reviews__is_approved=True))` в методе
`AttractionQuerySet.with_rating()`. Так исключены расхождения между
сохранённым и фактическим значением, а в списках рейтинг всех объектов
берётся одним запросом.
