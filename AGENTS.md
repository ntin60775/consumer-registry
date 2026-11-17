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

## Границы

- живые реестры `registry.local.json` живут вне git — в репо их нет;
- имена потребителей в репо не попадают;
- скрипты и тесты — stdlib-only Python 3;
- `deploy_log` и `acceptance` — append-only: отменённый шаг — новая запись;
- ломающие изменения контракта — только `consumer-registry/2`.

## Локальный OntoShip-флоу

Разработка этого репо идёт через OntoShip: состояние работы —
`docs/ops/continue.md`, сессия продолжается оттуда. Слой `.agents/`,
`.zcode/`, `docs/`, `tickets/` в git не входит — остаётся локальным
(решение оператора 2026-11-02).
