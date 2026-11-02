---
name: consumer-registry
description: "Реестр потребителей проекта — машино-локальный .zcode/registry.local.json вне git: кто и на чём потребляет проект, append-only журналы раскаток (deploy_log) и приёмок (acceptance), followups с done=false перед следующей поставкой. Контракт consumer-registry/1; схема и каркас в .zcode/registry/templates, валидатор — .zcode/registry/scripts/registry_check.py."
when_to_use: после каждого акта поставки/раскатки/снятия у потребителя; после приёмки; перед выпуском новой версии — сверка парка потребителей и незакрытых followups; на вопрос «кто и на какой версии нас использует».
license: MIT
metadata: { concern: process, contract: consumer-registry/1 }
---

# Реестр потребителей проекта

Машино-локальный реестр потребителей ПРОЕКТА (producer-side): кто и на чём
потребляет проект, акты раскаток и приёмок, незакрытые обязательства.
Файл — `<проект>/.zcode/registry.local.json`, контракт `consumer-registry/1`;
живёт вне git и не переносится между машинами. Схема и каркас —
`.zcode/registry/templates/`, валидатор —
`.zcode/registry/scripts/registry_check.py` (stdlib-only).

Начало ведения: скопируй каркас
`.zcode/registry/templates/registry.template.json` в
`.zcode/registry.local.json`, заполни `machine` и `project` по факту,
добавь в `.gitignore` строку из
`.zcode/registry/templates/gitignore.snippet`.

## Ядро правил

1. **Запись — после каждого акта**: раскатка/обновление/снятие у потребителя,
   приёмка, доклад потребителя о готовности — дополнил журнал/`consumers`,
   обновил `updated_at`.
2. **Журналы append-only**: отменённый шаг — новая запись, не правка старой.
3. **followups с `done: false`** — сверять ПЕРЕД следующей поставкой,
   закрывать по факту.
4. **Версии — не дублировать**: факт потребления и процесс здесь; историю
   версий держат источник у потребителя (deployed.json) и пин каталога.
5. **Машино-локальность**: файл вне git, между машинами не переносится;
   у воркспейса-копии — свой.
6. **Ломающие изменения** — новый контракт `consumer-registry/2`, не правка
   полей на месте.

## Проверка реестра

```sh
python3 .zcode/registry/scripts/registry_check.py .zcode/registry.local.json
```

Валидатор проверяет реестр по схеме `consumer-registry/1` и ISO-форматы
`updated_at` и `since`; второй аргумент переопределяет путь схемы.
Внешних зависимостей нет.
