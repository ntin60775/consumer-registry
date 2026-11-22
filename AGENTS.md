# consumer-registry — вход для агента

Самостоятельный DSH-поставляемый бандл: проект ведёт машино-локальный
реестр своих потребителей (контракт `consumer-registry/1`). Состав репо:
бандл `skills/consumer-registry/` (SKILL.md, `templates/` — схема, каркас,
gitignore-сниппет, `scripts/registry_check.py` — stdlib-only валидатор),
установщик `scripts/install.sh` (link/copy/check одного бандла), тесты
`tests/test_registry.py`.

## Проверки

- тесты бандла: `python3 tests/test_registry.py` — зелёные без внешних
  зависимостей;
- валидатор на каркасе:
  `python3 skills/consumer-registry/scripts/registry_check.py skills/consumer-registry/templates/registry.template.json`;
- установка: `scripts/install.sh --check <проект>` — `check: ok`.

## Версии и релизы

- версия — тег `vX.Y.Z` на tip `main` после зелёных проверок; тег не
  переносится, ошибка чинится новым тегом;
- слом контракта — новый `consumer-registry/N+1` и MAJOR, не правка
  полей на месте;
- правки вне бандла (доки, тесты, процессы) тега не требуют.

## Границы

- живые реестры `registry.local.json` живут вне git — в репо их нет;
- имена потребителей в репо не попадают;
- скрипты и тесты — stdlib-only Python 3;
- `deploy_log` — append-only: отменённый шаг — новая запись; `acceptance`
  не ведётся (поле схемы оставлено для чтения старых реестров);
- ломающие изменения контракта — только `consumer-registry/2`.

## Локальный OntoShip-флоу

Разработка этого репо идёт через OntoShip: состояние работы —
`docs/ops/continue.md`, сессия продолжается оттуда. Слой `.agents/`,
`.zcode/`, `docs/`, `tickets/` в git не входит — остаётся локальным
(решение оператора 2026-11-02).

<!-- BEGIN ontoship -->
## База знаний (OntoShip)

- Точка входа: [`docs/README.md`](docs/README.md) — главный индекс KB; у каждой папки
  есть индекс `README.md`.
- Ищи до ответа или записи: загрузи скилл `kb-search`. Движок лежит в
  `.agents/skills/kb-search/gitmark.py`; корень — `.agents/skills`.
- Новые или обновлённые документы: загрузи скилл `kb-curate` — сначала поиск, никогда
  не дублируй.
- Сопровождение после правки документов:

  ```sh
  python3 .agents/skills/kb-search/gitmark.py index
  python3 .agents/skills/kb-search/gitmark.py lint --strict
  python3 .agents/skills/kb-search/gitmark.py map -o docs-map.html
  ```

- KB — это markdown + git: `.gitmark/`, `*-map.html` и `.scratch/` производные или
  эфемерные — никогда не коммитятся.

## Вход в работу (OntoShip)

- Изменения этого проекта идут через ship-флоу: скилл `ship` исполняет
  один тикет за запуск — вручную командой `/ship`; свободные правки
  в обход тикета не делаются — прямые решения оператора выше этого
  правила.
- Запрос плана открывает draft-спеку через скилл `grilling`; режим плана
  харнесса не используется.
- Состояние и порядок работы — [docs/ops/continue.md](docs/ops/continue.md):
  сессия продолжается оттуда и берёт следующий тикет оттуда же.
- Команды: «стартуй юнит» — открыть draft-спеку; `ship` — командой
  `/ship` или «исполняй тикет N»; «деплой и обновление [имя_проекта]» —
  скилл `deliver`.
<!-- END ontoship -->
