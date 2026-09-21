# Журнал изменений

## 2026-09-21 — Диагностика, ретраи Replicate, чистка репозитория

### Диагностика бота на сервере (swift-violet)

Бот не «сломан», но падала генерация/анализ изображений. Запущен через `screen` + venv, один экземпляр, polling активен. Проверены:

- **Git:** сервер на ветке `feature/catalog-navigation`, синхронно с `origin`. Каталог-навигация на активной ветке.
- **Модели Replicate:** `anthropic/claude-4.5-sonnet`, `anthropic/claude-4.5-haiku`, `google/nano-banana-pro` — все существуют (HTTP 200). Менять модель не нужно (Sonnet 4.5 уже в `config.py`).

### Найденные причины ошибок

1. **429 Too Many Requests** от Replicate — «less than $5.0 in credit», троттлинг 6 req/min + burst=1. После пополнения баланса запросы проходят.
2. **E003 high demand** — разовая перегрузка на стороне Replicate.
3. **Прошлые конфликты «two bot instances»** (24 авг) — были при запуске через Docker и screen одновременно. Сейчас один экземпляр, устранено.
4. Сетевые сбои Telegram (reset/bad gateway/timeout) — транзиентные, aiogram их сам переживает. Не баг кода.

### Правка кода: ретраи для Replicate (`services.py`, коммит `c5aa7be`)

Добавлен хелпер `_replicate_call` — до 4 попыток с экспоненциальным backoff, учитывает `retry_after` из ответа сервера. Применён к `_replicate_run` (анализ текста) и `_generate_sync` (NanaBanana Pro). Цензурные ошибки не ретраятся (идут в `CensorshipError`). Стримы `BytesIO` перематываются между попытками (`seek(0)`).

После правки бот перезапущен, старт без ошибок, каталог загрузился (70 items).

### Чистка репозитория (коммит `09fde7c`)

Удалён устаревший прототип `Прототип — Telegram-бот NanoBanana.md` (22.5KB, тексты сообщений уже в `bot.py`). Обновлён `.gitignore`: добавлены `bot.log`, `*.log`, `data/` (runtime-логи и кэш). README остаётся единым источником правды.

### Восстановление истории (этот коммит)

`WIKI.md` (история этапов 1–12) и `CHANGELOG.md` (журнал изменений) восстановлены — история работы над ботом должна сохраняться. README остаётся кратким справочником, WIKI — хронологией этапов, CHANGELOG — журналом по сессиям.

### Полезное на будущее

- Коммиты пушатся через PAT (использовался одноразовый токен — после работы отозвать в GitHub → Settings → Developer settings → Personal access tokens).
- Бот запущен в `screen`-сессии `bot`. Лог: `tail -f ~/bot/bot.log`. При 429 теперь видно `Replicate transient error (attempt N/4), retrying in ...s`.


## 2026-09-21 — Claude Sonnet 4.5 и активная ветка каталога

### Модель для написания промптов

В `config.py` модель для анализа изображений и создания промптов в потоках `/reference`, `/describe` и `/style` заменена:

```python
ANALYSIS_MODEL = "anthropic/claude-4.5-sonnet"
```

Для коротких вспомогательных задач используется:

```python
FAST_MODEL = "anthropic/claude-4.5-haiku"
```

### Активная ветка и сервер

Основная рабочая ветка для текущего варианта проекта:

```text
feature/catalog-navigation
```

Рабочая копия бота находится на сервере `swift-violet` в каталоге `~/bot`.

Бот запускается из виртуального окружения Python 3.14:

```bash
~/bot/venv/bin/python bot.py
```

После изменения `config.py` процесс нужно перезапустить, потому что конфигурация читается при запуске приложения:

```bash
cd ~/bot
git pull origin feature/catalog-navigation
screen -S bot -X quit 2>/dev/null || true
screen -dmS bot bash -lc 'cd ~/bot && exec ~/bot/venv/bin/python -u bot.py >> ~/bot/bot.log 2>&1'
```

Проверка ветки и модели:

```bash
cd ~/bot
git branch --show-current
git log -1 --oneline
~/bot/venv/bin/python -c 'import config; print(config.ANALYSIS_MODEL)'
```

Ожидаемая модель:

```text
anthropic/claude-4.5-sonnet
```

После тестового запроса в Telegram фактический вызов можно проверить в логе:

```bash
grep -E 'claude-4(-|\\.5-)(sonnet|haiku)' ~/bot/bot.log | tail -20
```

### Python 3.14

Системный `/usr/bin/python3` не содержит зависимости проекта. Используйте только Python из окружения:

```bash
~/bot/venv/bin/python
```

Если зависимости нужно переустановить, для Python 3.14 может потребоваться:

```bash
PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 \
~/bot/venv/bin/python -m pip install -r requirements.txt
```

### Ошибки Replicate

Ошибки `402 Insufficient credit`, `429 Request was throttled` и `E003 Service is currently unavailable due to high demand` относятся к балансу, лимитам или временной доступности Replicate. Они не означают ошибку переключения модели в коде.
