# image creator | INTIMNO Bot

Telegram-бот для генерации профессиональных фотографий белья через NanaBanana Pro (Replicate).

---

## Что умеет бот

| Команда | Описание | Результат |
|---------|----------|-----------|
| `/reference` | Пользователь присылает референс-фото → бот анализирует стиль через Claude и составляет промпты → пользователь присылает фото трусов → генерация | 2 PNG-файла |
| `/style` | Пользователь присылает фото трусов → выбирает стиль из 4 → генерация | 3 PNG-файла |
| `/describe` | Пользователь описывает стиль текстом → Claude составляет промпт → пользователь присылает фото трусов → генерация | 1 PNG-файл |
| `/styles` | Описание всех 4 стилей | — |
| `/help` | Подробная справка | — |
| `/cancel` | Отменить текущее действие | — |

**Доп. элементы** — после получения фото трусов в любом из flow бот предлагает добавить в кадр: визитку INTIMNO, журнал INTIMNO, любой реквизит словами или фото.

### Стили (/style)

- **🌸 Нежный** — пастельные тона, мягкий свет, цветы, сатин, утренняя атмосфера
- **🌑 Тёмный** — тёмные фоны, свечи, парфюм, контрастный свет, luxury
- **💎 Rich** — белый шёлк / мрамор / бархат, золотые аксессуары, журнал INTIMNO
- **🎲 Смешанное** — разные атмосферы, неожиданные сочетания

---

## Технологии

- **Python 3.11+**
- **aiogram 3.x** — Telegram Bot framework (async, FSM)
- **Replicate API** — платформа для запуска моделей:
  - `anthropic/claude-4-sonnet` — анализ референс-изображений, создание промптов
  - `google/nano-banana-pro` — генерация изображений
- **aiohttp** — скачивание готовых изображений перед отправкой

---

## Структура проекта

```
bot-for-images/
├── bot.py          # Главный файл: хэндлеры, FSM, запуск
├── config.py       # Загрузка переменных из .env
├── states.py       # Состояния FSM (ReferenceFlow, StyleFlow, DescribeFlow)
├── prompts.py      # Промпты для 4 стилей (по 3 штуки каждый)
├── services.py     # Вызовы Replicate API (анализ + генерация)
├── .env            # Секреты (не коммитить)
├── .env.example    # Шаблон переменных
└── requirements.txt
```

---

## Быстрый старт

### 1. Клонировать / скачать проект

### 2. Создать виртуальное окружение и установить зависимости

```bash
python3 -m venv venv
source venv/bin/activate       # macOS / Linux
# venv\Scripts\activate        # Windows

pip install -r requirements.txt
```

### 3. Заполнить `.env`

```env
TELEGRAM_TOKEN=ваш_токен_от_BotFather
REPLICATE_API_TOKEN=ваш_токен_от_replicate.com
```

Где получить:
- **TELEGRAM_TOKEN** — создать бота через [@BotFather](https://t.me/BotFather), команда `/newbot`
- **REPLICATE_API_TOKEN** — [replicate.com](https://replicate.com) → Account → API Tokens

### 4. Запустить

```bash
python bot.py
```

---

## Деплой на сервер (VPS)

### Через systemd (рекомендуется)

Создать файл `/etc/systemd/system/nanabanana.service`:

```ini
[Unit]
Description=NanaBanana Telegram Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/bot-for-images
ExecStart=/home/ubuntu/bot-for-images/venv/bin/python bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Затем:
```bash
sudo systemctl daemon-reload
sudo systemctl enable nanabanana
sudo systemctl start nanabanana
sudo systemctl status nanabanana   # проверить статус
```

Логи:
```bash
journalctl -u nanabanana -f
```

### Через screen (быстрый вариант)

```bash
screen -S bot
python bot.py
# Ctrl+A, затем D — отсоединиться, бот продолжит работу
screen -r bot   # вернуться
```

---

## Переменные окружения

| Переменная | Описание |
|------------|----------|
| `TELEGRAM_TOKEN` | Токен бота от BotFather |
| `REPLICATE_API_TOKEN` | API-ключ Replicate |

---

## Параметры генерации (NanaBanana Pro)

| Параметр | Значение |
|----------|----------|
| `aspect_ratio` | `3:4` (всегда вертикальный кадр) |
| `resolution` | `1K` |
| `output_format` | `png` |
| `safety_filter_level` | `block_only_high` |

---

## Контакт

По вопросам работы бота: [@oreobra](https://t.me/oreobra)
