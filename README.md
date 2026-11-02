# consumer-registry

Опциональный плагин маркетплейса
[sot-zcode-marketplace](https://github.com/ntin60775/sot-zcode-marketplace):
проект ведёт реестр **своих потребителей** — машино-локальный
`.zcode/registry.local.json` вне git, контракт `consumer-registry/1`,
append-only журналы раскаток и приёмок, followups с `done: false` перед
следующей поставкой. Кому реестр не нужен, тот ничего не ставит: навык
необязателен.

## Установка

Ставится из каталога маркетплейса (канал `project`). После установки
`deploy.json` кладёт в проект:

- `.zcode/skills/consumer-registry/` — навык с правилами ведения;
- `.zcode/registry/templates/` — схема `registry.schema.json`, каркас
  `registry.template.json`, строка `gitignore.snippet` для `.gitignore`;
- `.zcode/registry/scripts/registry_check.py` — stdlib-only валидатор.

## Начало ведения

1. Скопируй каркас:
   `cp .zcode/registry/templates/registry.template.json .zcode/registry.local.json`.
2. Заполни `machine` (hostname, operator) и `project` (имя, путь репо) по факту.
3. Добавь в `.gitignore` строку из `.zcode/registry/templates/gitignore.snippet`.
4. Веди реестр по правилам навыка `consumer-registry`: после каждого акта —
   запись в журнал и обновление `updated_at`.

## Проверка реестра

```sh
python3 .zcode/registry/scripts/registry_check.py .zcode/registry.local.json
```

Валидатор — Python 3 без внешних зависимостей: проверяет реестр по схеме
`consumer-registry/1` и ISO-форматы `updated_at` и `since`. Схема по
умолчанию берётся как `../templates/registry.schema.json` от скрипта,
второй аргумент переопределяет путь.

## Разработка

```sh
python3 tests/test_registry.py
python3 scripts/registry_check.py templates/registry.template.json
```

Тесты — stdlib-only, без внешних зависимостей.

## Границы

- живые реестры `registry.local.json` — вне git, в репо их нет;
- имена потребителей в репо не попадают;
- скрипты и тесты — stdlib-only Python 3;
- `deploy_log` и `acceptance` — append-only: отменённый шаг — новая запись;
- ломающие изменения контракта — только `consumer-registry/2`.

Лицензия — MIT (`LICENSE`).
