# image creator | INTIMNO Bot

Telegram-бот для генерации профессиональных product-фотографий женского белья (трусы) и навигации по каталогу артикулов для бренда **INTIMNO**.

> **Активная ветка на сервере:** `feature/catalog-navigation`  
> **Базовая ветка:** `feature/panties-analysis-feedback-v2`  
> **Сервер:** `swift-violet` (SSH: `rodkin@swift-violet`), директория `~/bot`  
> **Запуск:** `screen -dmS bot ~/bot/venv/bin/python bot.py` от пользователя `rodkin` (без Docker, Python 3.14 + venv)

---

## Что умеет бот

### 🎨 Генерация контента

| Команда | Описание | Результат |
|---------|----------|-----------|
| `/reference` | Пользователь присылает фото трусов → анализ материала/цвета → пользователь присылает референс-фото → Claude составляет 2 промпта → генерация | 2 PNG-файла |
| `/style` | Пользователь присылает фото трусов → анализ → выбирает стиль из **5** → Claude генерирует 2 уникальных промпта → генерация | 2 PNG-файла |
| `/describe` | Пользователь присылает фото трусов → анализ → описывает стиль текстом → Claude составляет промпт → генерация | 1 PNG-файл |
| `/help` | Справка по всем функциям | — |
| `/cancel` | Отменить текущее действие | — |

**Доп. элементы** — после анализа трусов в любом flow бот предлагает добавить в кадр: визитку INTIMNO, журнал INTIMNO, аксессуары в тон, любой реквизит словами или фото.

**Фидбэк** — после каждой генерации бот предлагает ответить на 4–5 динамических вопросов кнопками. Ответы сохраняются в `feedback_notes.json` и учитываются в будущих генерациях.

### Стили (/style)

- **Нежный** — пастельные тона, мягкий свет, цветы, сатин, утренняя атмосфера
- **Тёмный** — тёмные фоны, свечи, парфюм, контрастный свет, luxury
- **Rich** — белый шёлк / мрамор / бархат, золотые аксессуары, журнал INTIMNO
- **Смешанное** — разные атмосферы, неожиданные сочетания
- **Цветотип** — вся палитра кадра осознанно строится вокруг оттенка трусов (аналоговая / комплементарная / монохромная гармония)

---

### 🗂 Навигация по артикулам

| Команда | Описание |
|---------|----------|
| `/catalog` | Полный каталог артикулов по категориям (Нижнее бельё / Быстрые запуски) с пагинацией |
| `/find` | Быстрый нечёткий поиск по названию артикула |

По каждому артикулу — кнопки с прямыми ссылками: **WB · Ozon · Исходники · Предметка · На моделях · Видео**

Данные берутся из Google Sheets (XLSX). Каталог обновляется автоматически раз в неделю.

---

## Главное меню (/start)

При входе бот показывает два раздела с inline-кнопками:
- **🎨 Генерация контента** → По референсу / Описать словами / Выбрать стиль
- **🗂 Навигация по артикулам** → Каталог / Найти артикул

---

## Технологии

- **Python 3.14**
- **aiogram 3.x** — Telegram Bot framework (async, FSM)
- **Replicate API** — платформа для запуска моделей:
  - `anthropic/claude-4-sonnet` — анализ изображений, создание промптов
  - `google/nano-banana-pro` — генерация изображений
- **aiohttp** — скачивание готовых изображений перед отправкой
- **openpyxl** — чтение XLSX из Google Sheets с сохранением гиперссылок
- **rapidfuzz** — нечёткий поиск по каталогу (без AI-токенов)

---

## Ветки

| Ветка | Статус | Описание |
|-------|--------|----------|
| `feature/panties-analysis-feedback-v2` | 🌿 **Базовая** | Анализ трусов, 5 стилей, Цветотип, фидбэк, строгое сохранение гарнмента |
| `feature/catalog-navigation` | ✅ **Активная (на сервере)** | Подветка feedback-v2 + навигация по каталогу, главное меню |
| `feature/multi-panties-images` | 📦 В архиве | Мультизагрузка фото (вошла в feedback-v2) |

> **Важно:** `main` — упразднён, больше не используется. Базовая ветка — `feature/panties-analysis-feedback-v2`.

---

## Структура проекта

```
bot/
├── bot.py              # Все хэндлеры, FSM, тексты, главное меню, запуск
├── catalog.py          # Загрузка каталога из Google Sheets (XLSX), кэш, поиск
├── config.py           # Загрузка переменных из .env
├── states.py           # Состояния FSM (ReferenceFlow, StyleFlow, DescribeFlow, CatalogFlow)
├── styles.py           # 5 стилей (STYLE_BLUEPRINTS) для /style
├── services.py         # Вся логика: анализ трусов, генерация промптов, генерация изображений
├── notes.py            # Чтение/запись feedback_notes.json
├── data/
│   └── feedback_notes.json  # Накопленные заметки из фидбэка (не коммитить)
├── .env                # Токены (не коммитить)
├── .env.example        # Шаблон переменных
├── requirements.txt
├── Dockerfile          # Оставлен про запас (не используется)
└── docker-compose.yml  # Оставлен про запас (не используется)
```

---

## Переменные окружения

| Переменная | Описание |
|------------|----------|
| `TELEGRAM_TOKEN` | Токен бота от BotFather |
| `REPLICATE_API_TOKEN` | API-ключ Replicate |
| `CATALOG_SHEET_URL` | URL Google Sheets (CSV-экспорт, задан в config.py) |

---

## Быстрый старт (локально)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Заполнить .env (см. .env.example)
python bot.py
```

---

## Деплой на сервер (VPS swift-violet)

> Бот запущен через `screen` + venv без Docker. Сервер использует **Python 3.14**.

### Обновление кода (рабочий цикл)

```bash
# 1. На Mac — закоммить и запушить
git add . && git commit -m "..." && git push origin feature/catalog-navigation

# 2. На сервере — подтянуть и перезапустить
ssh rodkin@swift-violet
cd ~/bot
git pull origin feature/catalog-navigation
pkill -f bot.py
screen -dmS bot ~/bot/venv/bin/python bot.py
```

### Первый деплой на новый сервер

```bash
ssh rodkin@swift-violet
git clone https://github.com/oreobra/image-creator-INTIMNO.git bot
cd bot
git checkout feature/catalog-navigation
nano .env   # TELEGRAM_TOKEN и REPLICATE_API_TOKEN

sudo apt update && sudo apt install python3-full python3-dev -y
python3 -m venv ~/bot/venv
PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 ~/bot/venv/bin/pip install -r requirements.txt

screen -dmS bot ~/bot/venv/bin/python bot.py
sleep 3 && screen -r bot
```

### Логи

```bash
screen -r bot        # подключиться к сессии бота
# Ctrl+A, D           # отсоединиться
```

### Восстановление после падения сервера

```bash
git clone https://github.com/oreobra/image-creator-INTIMNO.git bot
cd bot
git checkout feature/catalog-navigation
nano .env   # восстановить токены
python3 -m venv ~/bot/venv
pip install -r requirements.txt
screen -dmS bot ~/bot/venv/bin/python bot.py
```

> ⚠️ **Токены нигде не хранятся в Git** — держи `TELEGRAM_TOKEN` и `REPLICATE_API_TOKEN` в надёжном месте.

---

## Параметры генерации (NanaBanana Pro)

| Параметр | Значение |
|----------|----------|
| `aspect_ratio` | `3:4` (вертикальный кадр) |
| `resolution` | `1K` |
| `output_format` | `png` |
| `safety_filter_level` | `block_only_high` |

---

## Контакт

По вопросам работы бота: [@oreobra](https://t.me/oreobra)
