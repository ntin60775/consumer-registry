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

1. Если файла `.agents/registry.local.json` нет — скопируй каркас:
   `cp .agents/skills/consumer-registry/templates/registry.template.json .agents/registry.local.json`.
   Файл уже есть — не перезаписывай: ведение начато, читай и дополняй.
2. Заполни `machine` (hostname, operator) и `project` (имя, путь репо) по факту.
3. Если строки `.agents/registry.local.json` в `.gitignore` нет — добавь её
   из `templates/gitignore.snippet` бандла (чужие строки не трогай, свою не
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

## Версии и релизы

Версия — git-тег `vMAJOR.MINOR.PATCH` на коммите `main`; отдельного файла
версии нет, источник истины — git.

- **MAJOR** — слом контракта `consumer-registry/N`: меняются поля,
  `required`-наборы или `const` схемы. Контракт на месте не правится:
  выпускается `consumer-registry/N+1` и новый MAJOR версии бандла.
- **MINOR** — поведение без слома: опциональные поля схемы, правила
  ведения, валидатор.
- **PATCH** — исправление без смены контракта.

Релиз:

1. `main` зелёный: тесты бандла и KB-линт репо.
2. Тег ставится на tip `main`: `git tag vX.Y.Z && git push origin vX.Y.Z`.
   Тег не переносится на другой коммит: ошибка чинится новым тегом.
3. Доказательство — установка с дерева тега: `git archive vX.Y.Z` во
   временный каталог, `scripts/install.sh --copy` в пустой проект, затем
   `--check: ok` и валидатор на каркасе.
4. `git ls-remote --tags origin vX.Y.Z` совпадает с локальным
   `git rev-parse --short vX.Y.Z`.

Правки вне бандла — документация, тесты, процессы — тега не требуют:
то, что получает потребитель, не меняется.

## Границы

- живые реестры `registry.local.json` — вне git, в репо их нет;
- имена потребителей в репо не попадают;
- скрипты и тесты — stdlib-only Python 3;
- `deploy_log` — append-only: отменённый шаг — новая запись; `acceptance`
  не ведётся (поле схемы оставлено для чтения старых реестров);
- ломающие изменения контракта — только `consumer-registry/2`.

Лицензия — MIT (`LICENSE`).
