# Журнал изменений

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
