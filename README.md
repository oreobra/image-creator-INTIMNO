# image creator | INTIMNO Bot

Telegram-бот для генерации профессиональных product-фотографий женского белья (трусы) для бренда **INTIMNO**.

> **Активная ветка на сервере:** `feature/panties-analysis-feedback-v2`  
> **Сервер:** `swift-violet` (SSH: `rodkin@swift-violet`), директория `~/bot`  
> **Запуск:** `nohup ~/bot/venv/bin/python bot.py` от пользователя `rodkin` (без Docker, Python 3.14 + venv)

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

> Бот запущен через `nohup` + виртуальное окружение (venv) без Docker.  
> Сервер использует **Python 3.14** — нужен специальный флаг при установке пакетов.

### Первый деплой на новый сервер (один раз)

```bash
ssh rodkin@swift-violet

# Клонировать репозиторий
git clone https://github.com/oreobra/image-creator-INTIMNO.git bot
cd bot
git checkout feature/panties-analysis-feedback-v2

# Создать .env с токенами
nano .env
# Вставить:
# TELEGRAM_TOKEN=...
# REPLICATE_API_TOKEN=...

# Установить системные зависимости (нужны для компиляции)
sudo apt update
sudo apt install python3-full python3-dev -y

# Создать виртуальное окружение
python3 -m venv ~/bot/venv

# Установить пакеты (флаг нужен из-за Python 3.14)
PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 ~/bot/venv/bin/pip install aiogram replicate python-dotenv aiohttp

# Создать лог-файл
touch ~/bot/bot.log

# Запустить бота
cd ~/bot && nohup ~/bot/venv/bin/python bot.py >> ~/bot/bot.log 2>&1 &

# Проверить что запустился
sleep 3 && tail -10 ~/bot/bot.log
```

### Обновление кода (рабочий цикл)

```bash
# 1. На Mac — закоммить и запушить изменения
git add . && git commit -m "..." && git push origin feature/panties-analysis-feedback-v2

# 2. На сервере — подтянуть и перезапустить
ssh rodkin@swift-violet
cd ~/bot
git pull origin feature/panties-analysis-feedback-v2

# Найти PID текущего процесса
ps aux | grep bot.py

# Убить старый процесс (подставить реальный PID)
kill <PID>

# Запустить с новым кодом
nohup ~/bot/venv/bin/python bot.py >> ~/bot/bot.log 2>&1 &

# Убедиться что запустился
sleep 3 && ps aux | grep bot.py
```

### Логи

```bash
tail -f ~/bot/bot.log
```

### Если сервер упал — восстановление

Всё хранится на GitHub. Нужно только пересоздать `.env` с токенами:

```bash
# Подключиться к новому серверу
ssh <user>@<новый_ip>

# Установить зависимости системы
sudo apt update && sudo apt install python3-full python3-dev git -y

# Клонировать нужную ветку
git clone https://github.com/oreobra/image-creator-INTIMNO.git bot
cd bot
git checkout feature/panties-analysis-feedback-v2

# Создать .env (токены хранить отдельно — в Git их нет!)
nano .env

# Создать venv и установить пакеты
python3 -m venv ~/bot/venv
PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 ~/bot/venv/bin/pip install aiogram replicate python-dotenv aiohttp

# Запустить
touch ~/bot/bot.log
cd ~/bot && nohup ~/bot/venv/bin/python bot.py >> ~/bot/bot.log 2>&1 &
sleep 3 && tail -10 ~/bot/bot.log
```

> ⚠️ **Токены нигде не хранятся в Git** — держи `TELEGRAM_TOKEN` и `REPLICATE_API_TOKEN` в надёжном месте (менеджер паролей).  
> Токены получить: **TELEGRAM_TOKEN** — [@BotFather](https://t.me/BotFather) → `/mybots` → API Token. **REPLICATE_API_TOKEN** — [replicate.com](https://replicate.com) → Account → API Tokens.

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
