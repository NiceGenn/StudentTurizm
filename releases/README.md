# Релизы

Сюда складываются выгрузки готовых версий проекта: архивы для сдачи,
резервные копии базы, экспортированные диаграммы и печатные материалы.

Сами архивы в git не попадают (`.gitignore` исключает `*.zip` и `*.tar.gz`) —
отслеживается только этот файл и описание версий.

## Как собрать архив версии

```bash
git archive --format=zip --prefix=StudentTurizm/ -o releases/v0.1.0.zip HEAD
```

## Как выгрузить базу

```bash
python sources/manage.py dumpdata catalog auth.User --indent 2 \
  > releases/content-$(date +%Y-%m-%d).json
```

Восстановление: `python sources/manage.py loaddata releases/<файл>.json`.
Фотографии лежат в `sources/media/` и в выгрузку не попадают — копируйте
эту папку отдельно.

## Версии

| Версия | Дата | Что вошло |
|---|---|---|
| 0.1.0 | — | Первая полная версия MVP, см. [CHANGELOG.md](../CHANGELOG.md) |
