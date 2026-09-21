# Журнал изменений

## 2026-09-21 — переход на Claude Sonnet 4.5

### Изменение модели

В `config.py` модель, которая анализирует изображения и пишет промпты для потоков `/reference`, `/describe` и `/style`, обновлена:

```python
ANALYSIS_MODEL = "anthropic/claude-4.5-sonnet"
```

`FAST_MODEL` для коротких вспомогательных задач оставлен без изменений:

```python
FAST_MODEL = "anthropic/claude-4.5-haiku"
```

Изменение также зафиксировано в базовой ветке `feature/panties-analysis-feedback-v2`.

### Серверный деплой

Рабочая копия находится на сервере `swift-violet` в `~/bot` и запускается через Python из виртуального окружения:

```bash
~/bot/venv/bin/python bot.py
```

После обновления `config.py` процесс необходимо перезапустить: модель загружается при старте Python-приложения. Рекомендуемый запуск в `screen`:

```bash
cd ~/bot
screen -S bot -X quit 2>/dev/null || true
screen -dmS bot bash -lc 'cd ~/bot && exec ~/bot/venv/bin/python -u bot.py >> ~/bot/bot.log 2>&1'
```

Проверка ветки, коммита и модели:

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

После тестового запроса в Telegram фактически вызванную модель можно проверить так:

```bash
grep -E 'claude-4(-|\\.5-)(sonnet|haiku)' ~/bot/bot.log | tail -20
```

### Важное замечание по Python 3.14

Сервер использует Python 3.14.4. Запускать бота нужно через `~/bot/venv/bin/python`, а не через системный `/usr/bin/python3`, поскольку зависимости установлены в виртуальном окружении.

Установка зафиксированных зависимостей из `requirements.txt` может потребовать ABI-флаг для `pydantic-core`:

```bash
PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 \
~/bot/venv/bin/python -m pip install -r requirements.txt
```

### Известные ошибки Replicate

Ошибки `402 Insufficient credit`, `429 Request was throttled` и `E003 Service is currently unavailable due to high demand` относятся к балансу, лимитам или временной доступности Replicate, а не к переключению модели в коде.
