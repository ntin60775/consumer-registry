# consumer-registry

Самостоятельный DSH-поставляемый бандл: проект ведёт реестр **своих
потребителей** — машино-локальный `.agents/registry.local.json` вне git,
контракт `consumer-registry/1`, append-only журналы раскаток и приёмок,
followups с `done: false` перед следующей поставкой. Кому реестр не нужен,
тот ничего не ставит: скилл необязателен.

## Установка

Свой установщик `scripts/install.sh` ставит один бандл
`consumer-registry` в `<проект>/.agents/skills/` (project-local корень
скиллов DSH):

```sh
scripts/install.sh <проект>           # link: симлинк на этот репо
scripts/install.sh --copy <проект>    # copy: detached-копия
scripts/install.sh --check <проект>   # проверка установки
```

Установка идемпотентна, пишет только `.agents/skills`, preflight
отказывает вместо полуустановки; drifted-копия — отказ «copy differs».
Бандл самонесущий: `skills/consumer-registry/` несёт `SKILL.md`,
`templates/` (схема `registry.schema.json`, каркас
`registry.template.json`, строка `gitignore.snippet`) и
`scripts/registry_check.py` — stdlib-only валидатор.

## Начало ведения

Старт ведения идемпотентен и описан в скилле `consumer-registry`:

1. Скопируй каркас:
   `cp .agents/skills/consumer-registry/templates/registry.template.json .agents/registry.local.json`.
2. Заполни `machine` (hostname, operator) и `project` (имя, путь репо) по факту.
3. Добавь в `.gitignore` строку `.agents/registry.local.json` из
   `templates/gitignore.snippet` бандла (чужие строки не трогай, свою не
   дублируй).
4. Веди реестр по правилам скилла: после каждого акта — запись в журнал и
   обновление `updated_at`.

Повторный старт ничего не меняет. **Снос `.agents` уничтожает реестр**;
бэкап/экспорт вне v1, потеря = ручное перенаполнение.

## Проверка реестра

```sh
python3 .agents/skills/consumer-registry/scripts/registry_check.py .agents/registry.local.json
```

Валидатор — Python 3 без внешних зависимостей: проверяет реестр по схеме
`consumer-registry/1` и ISO-форматы `updated_at` и `since`. Схема по
умолчанию берётся как `../templates/registry.schema.json` от скрипта,
второй аргумент переопределяет путь.

## Разработка

```sh
python3 tests/test_registry.py
python3 skills/consumer-registry/scripts/registry_check.py skills/consumer-registry/templates/registry.template.json
```

Тесты — stdlib-only, без внешних зависимостей.

## Границы

- живые реестры `registry.local.json` — вне git, в репо их нет;
- имена потребителей в репо не попадают;
- скрипты и тесты — stdlib-only Python 3;
- `deploy_log` и `acceptance` — append-only: отменённый шаг — новая запись;
- ломающие изменения контракта — только `consumer-registry/2`.

Лицензия — MIT (`LICENSE`).
