# Ceyona CI — Architecture-Governed Pipeline

## Что делает этот CI

```
push / PR
  ↓
[1] lint-fix        — ruff + isort, auto-commit fix
  ↓
[2] architecture    — layer contracts, forbidden imports, circular deps
[3] test            — imports, lint, pytest + coverage ≥ 60%
  ↓
[4] security        — pip-audit (CVE), bandit (SAST)
  ↓
[5] deploy-searxng  — только main branch
[6] deploy          — только main branch, нужны architecture + test + security
  ↓
[7] healthcheck     — /health + /providers после деплоя
```

---

## Файлы

| Файл | Назначение |
|---|---|
| `.github/workflows/ci.yml` | Основной pipeline |
| `.github/dependabot.yml` | Автообновление зависимостей (еженедельно) |
| `.pre-commit-config.yaml` | Хуки для локальной проверки до push |
| `project-root/.importlinter` | Контракты слоёв (import-linter) |
| `project-root/scripts/check_imports.py` | Скрипт проверки границ — используют CI и pre-commit |
| `project-root/tests/test_epk_governance.py` | Регрессия EPK порогов + cost model |
| `project-root/tests/test_meta_isolation.py` | META layer не контролирует execution |
| `project-root/tests/test_architecture_contracts.py` | Статическая проверка всех layer contracts |

---

## Локальная установка

```bash
# Pre-commit (один раз):
pip install pre-commit
pre-commit install

# Теперь при каждом git commit автоматически запускается:
# ruff, isort, trailing-whitespace, yaml-check, forbidden-imports

# Запустить на всех файлах вручную:
pre-commit run --all-files

# Проверить архитектуру вручную:
cd project-root
python scripts/check_imports.py

# Запустить тесты с coverage:
pytest --cov=. --cov-report=term-missing --cov-fail-under=60
```

---

## Что защищается автоматически

### Layer contracts (architecture.md §19)
- `transport` не достаёт `cognition` internals
- `agents` не трогают `infra` / `payments`
- `meta` никогда не контролирует execution
- `retrieval` не зависит от `transport` / speech
- `contracts` остаётся чистым (нет runtime deps)
- `cost_model` ↔ `model_router` независимы (§8)
- `observability` только читает

### EPK governance
- Пороги `DENY / DEGRADE / HEAVY / ALLOW` не дрейфуют
- `GENERAL_CEILING == DEGRADE_THRESHOLD` (synchronization contract)
- `MAX_OUTPUT_CAP < _MAX_TOKENS` (разные authority — §8)
- Free trial ($0.10) покрывает минимальный viable usage

### META isolation
- `correction.py` и `output_normalizer.py` выполняются только внутри synthesizer (шаги 5/6)
- META модули не экспортируют routing/tier/EPK атрибуты
- Порядок 7-step pipeline зафиксирован

### Security
- CVE в зависимостях (pip-audit, еженедельно через Dependabot)
- Static security analysis (bandit MEDIUM/HIGH)

---

## Добавить позже (из audit.md open items)

- [ ] Coverage floor поднять до 75% после добавления speech/billing тестов
- [ ] `pytest-asyncio` stress tests для async race conditions (13.4)
- [ ] Integration tests: compound_agent tool execution (13.1 regression)
- [ ] Retrieval quality regression: query → expected docs → minimum score
- [ ] mypy type checking (добавить в `[project.optional-dependencies].dev`)