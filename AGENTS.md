# consumer-registry — вход для агента

Плагин маркетплейса
[sot-zcode-marketplace](https://github.com/ntin60775/sot-zcode-marketplace):
проект ведёт машино-локальный реестр своих потребителей (контракт
`consumer-registry/1`). Состав репо: навык `skills/consumer-registry/`,
шаблоны `templates/` (схема, каркас, gitignore-сниппет), stdlib-only
валидатор `scripts/registry_check.py`, тесты `tests/test_registry.py`.

## Проверки

- тесты плагина: `python3 tests/test_registry.py` — зелёные без внешних
  зависимостей;
- валидатор на каркасе:
  `python3 scripts/registry_check.py templates/registry.template.json`.

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
