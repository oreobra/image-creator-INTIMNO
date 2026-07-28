# image creator | INTIMNO Bot

Telegram-бот для генерации профессиональных product-фотографий женского белья (трусы) для бренда **INTIMNO**.

> **Активная ветка на сервере:** `feature/panties-analysis-feedback-v2`  
> **Сервер:** `zbbodhuzwo` (SSH: `oreobra@zbbodhuzwo`), директория `~/bot`  
> **Запуск:** прямой процесс `python bot.py` от root (без Docker)

---

## Что умеет бот

| Команда | Описание | Результат |
|---------|----------|-----------|
| `/reference` | Пользователь присылает референс-фото → бот анализирует стиль через Claude → пользователь присылает фото трусов (одно или несколько) → генерация | 2 PNG-файла |
| `/style` | Пользователь присылает фото трусов → анализ материала/цвета → выбирает стиль из **5** → Claude генерирует 2 уникальных промпта → генерация | 2 PNG-файла |
| `/describe` | Пользователь описывает стиль текстом → Claude составляет промпт → пользователь присылает фото трусов (одно или несколько) → генерация | 1 PNG-файл |
| `/styles` | Описание всех 5 стилей | — |
| `/help` | Подробная справка | — |
| `/cancel` | Отменить текущее действие | — |

**Доп. элементы** — после получения фото трусов в любом из flow бот предлагает добавить в кадр: визитку INTIMNO, журнал INTIMNO, аксессуары в тон, любой реквизит словами или фото.

**Фидбэк** — после каждой генерации бот предлагает ответить на 4–5 динамических вопросов кнопками. Ответы сохраняются в `feedback_notes.json` и учитываются в будущих генерациях.

### Стили (/style)

- **🌸 Нежный** — пастельные тона, мягкий свет, цветы, сатин, утренняя атмосфера
- **🌑 Тёмный** — тёмные фоны, свечи, парфюм, контрастный свет, luxury
- **💎 Rich** — белый шёлк / мрамор / бархат, золотые аксессуары, журнал INTIMNO
- **🎲 Смешанное** — разные атмосферы, неожиданные сочетания
- **🎨 Цветотип** — вся палитра кадра осознанно строится вокруг оттенка трусов (аналоговая / комплементарная / монохромная гармония)

---

## Технологии

- **Python 3.11+**
- **aiogram 3.x** — Telegram Bot framework (async, FSM)
- **Replicate API** — платформа для запуска моделей:
  - `anthropic/claude-4-sonnet` — анализ референс-изображений, создание промптов
  - `google/nano-banana-pro` — генерация изображений
- **aiohttp** — скачивание готовых изображений перед отправкой

---

## Ветки и деплой

| Ветка | Статус | Описание |
|-------|--------|----------|
| `feature/panties-analysis-feedback-v2` | ✅ **На сервере** | Актуальная рабочая версия: анализ трусов, 5 стилей, Цветотип, фидбэк, строгое сохранение гарнмента |
| `feature/multi-panties-images` | 📦 В архиве | Мультизагрузка фото трусов (вошла в feature-ветку выше) |
| `main` | 📦 Устарел | Старая базовая версия без анализа и фидбэка |

> **Важно:** `main` — не актуален. Работай с веткой `feature/panties-analysis-feedback-v2`.

---

## Структура проекта

```
bot/
├── bot.py              # Все хэндлеры, FSM, тексты сообщений, запуск
├── config.py           # Загрузка переменных из .env
├── states.py           # Состояния FSM (ReferenceFlow, StyleFlow, DescribeFlow)
├── styles.py           # 5 стилей (STYLE_BLUEPRINTS) для /style
├── services.py         # Вся логика: анализ трусов, генерация промптов, генерация изображений, фидбэк
├── notes.py            # Чтение/запись feedback_notes.json
├── data/
│   └── feedback_notes.json  # Накопленные заметки из фидбэка (не коммитить)
├── .env                # Токены (не коммитить)
├── .env.example        # Шаблон переменных
├── requirements.txt
├── Dockerfile          # Образ (не используется сейчас, оставлен про запас)
└── docker-compose.yml  # Не используется сейчас, оставлен про запас
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

> Сейчас бот запущен напрямую через `nohup python bot.py` от root. Docker не используется.

### Первый деплой (один раз)

```bash
ssh oreobra@zbbodhuzwo
git clone git@github.com:oreobra/image-creator-INTIMNO.git bot
cd bot
git checkout feature/panties-analysis-feedback-v2
nano .env    # вставить TELEGRAM_TOKEN и REPLICATE_API_TOKEN
pip install -r requirements.txt
sudo bash -c "cd /home/oreobra/bot && nohup python bot.py >> /home/oreobra/bot/bot.log 2>&1 &"
```

### Обновление кода (рабочий цикл)

```bash
# 1. На Mac — закоммить и запушить изменения
git add . && git commit -m "..." && git push origin feature/panties-analysis-feedback-v2

# 2. На сервере — подтянуть и перезапустить
ssh oreobra@zbbodhuzwo
cd ~/bot
git pull origin feature/panties-analysis-feedback-v2

# Найти PID текущего процесса
ps aux | grep bot.py

# Убить старый процесс (подставить реальный PID)
sudo kill <PID>

# Запустить с новым кодом
sudo bash -c "cd /home/oreobra/bot && nohup python bot.py >> /home/oreobra/bot/bot.log 2>&1 &"

# Убедиться что запустился
ps aux | grep bot.py
```

### Логи

```bash
sudo tail -f /home/oreobra/bot/bot.log
```

### Если сервер упал и нужно восстановить

```bash
# Всё необходимое хранится на GitHub в ветке feature/panties-analysis-feedback-v2
# Достаточно:
# 1. Склонировать репозиторий на новый сервер
# 2. Переключиться на нужную ветку
# 3. Заполнить .env (токены хранятся отдельно — не в Git!)
# 4. Запустить бота

git clone git@github.com:oreobra/image-creator-INTIMNO.git bot
cd bot
git checkout feature/panties-analysis-feedback-v2
nano .env
pip install -r requirements.txt
sudo bash -c "cd /home/oreobra/bot && nohup python bot.py >> /home/oreobra/bot/bot.log 2>&1 &"
```

> ⚠️ **Токены нигде не хранятся в Git** — держи их в надёжном месте отдельно (менеджер паролей, заметки с защитой). Нужны: `TELEGRAM_TOKEN` и `REPLICATE_API_TOKEN`.

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
