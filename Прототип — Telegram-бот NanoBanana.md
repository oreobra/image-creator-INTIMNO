# Telegram-бот NanaBanana Studio — Документация

> Версия: 2.0 — апрель 2026  
> Контакт для вопросов: @oreobra  
> Репозиторий: github.com/oreobra/image-creator-INTIMNO

---

## 1. ЧТО ДЕЛАЕТ БОТ

Бот генерирует профессиональные фотографии женского белья (трусы) через NanaBanana Pro на платформе Replicate. Анализирует референсы и текстовые описания через Claude Sonnet, составляет промпты и запускает генерацию. Без фото трусов генерация не запускается — жёсткое условие.

**Бренд дополнительных элементов:** INTIMNO

---

## 2. ФУНКЦИИ БОТА

### Функция 1 — «По референсу» (`/reference`)
Пользователь присылает любое понравившееся изображение → Claude анализирует стиль, угол, свет, фон, настроение → составляет **2 варианта промпта** → просит прислать фото трусов → предлагает добавить доп. элементы → запускает **2 генерации параллельно** → возвращает **2 PNG-файла**.

### Функция 2 — «По стилю» (`/style`)
Пользователь присылает фото трусов → выбирает стиль из меню **4 стилей** → предлагаются доп. элементы → бот прогоняет **3 промпта** выбранного стиля параллельно через NanaBanana Pro → отправляет **3 PNG-файла**.

### Функция 3 — «Описать стиль» (`/describe`)
Пользователь описывает стиль текстом (на русском или английском) → Claude составляет промпт → просит прислать фото трусов → предлагает доп. элементы → генерирует **1 PNG-файл**.

### Доп. элементы (во всех функциях)
После получения фото трусов в любой функции бот предлагает добавить в кадр:
- 📇 Визитку с брендом INTIMNO
- 📖 Журнал INTIMNO
- ✏️ Любой реквизит словами
- 🖼 Реквизит фотографией (Claude анализирует и описывает его)
- ✅ Без добавок — сразу к генерации

---

## 3. ЛОГИКА И СЦЕНАРИИ (FLOWS)

### Flow 1 — По референсу

```
Пользователь → /reference
     ↓
Бот просит прислать референс-изображение
     ↓
Пользователь → присылает референс (фото или файл PNG/JPG/JPEG)
     ↓
Claude анализирует: тип кадра, угол, свет, фон, пропсы, настроение
     ↓
Бот составляет 2 варианта промпта и показывает их пользователю
     ↓
Бот просит прислать фото трусов
     ↓
Пользователь → присылает фото трусов (фото или файл)
     ↓
Бот показывает меню доп. элементов
     ↓
Пользователь → выбирает элемент или «Без добавок»
     ↓
Бот запускает 2 генерации параллельно в NanaBanana Pro
     ↓
Бот отправляет 2 PNG-файла пользователю
```

---

### Flow 2 — По стилю

```
Пользователь → /style
     ↓
Бот просит прислать фото трусов
     ↓
Пользователь → присылает фото трусов (фото или файл)
     ↓
Бот показывает меню стилей:
     [🌸 Нежный]  [🌑 Тёмный]
     [💎 Rich]    [🎲 Смешанное]
     ↓
Пользователь выбирает стиль
     ↓
Бот показывает меню доп. элементов
     ↓
Пользователь → выбирает элемент или «Без добавок»
     ↓
Бот запускает 3 промпта выбранного стиля параллельно в NanaBanana Pro
     ↓
Бот отправляет 3 PNG-файла пользователю
```

---

### Flow 3 — Описать стиль

```
Пользователь → /describe
     ↓
Бот просит описать стиль словами
     ↓
Пользователь → пишет описание (русский или английский)
     ↓
Claude составляет промпт по описанию и показывает его
     ↓
Бот просит прислать фото трусов
     ↓
Пользователь → присылает фото трусов (фото или файл)
     ↓
Бот показывает меню доп. элементов
     ↓
Пользователь → выбирает элемент или «Без добавок»
     ↓
Бот генерирует 1 изображение в NanaBanana Pro
     ↓
Бот отправляет PNG-файл пользователю
```

---

### Flow доп. элементов (шаг внутри всех flow)

```
Бот показывает меню:
[📇 Визитка]          [📖 Журнал INTIMNO]
[✏️ Описать словами]  [🖼 Прислать фото]
[✅ Без добавок — генерировать]
     ↓
Визитка → добавляет в промпт: "a small elegant business card with brand name INTIMNO placed beside"
Журнал  → добавляет в промпт: "an INTIMNO brand magazine placed beside"
Описать → пользователь пишет текст → добавляется в промпт
Фото    → пользователь присылает фото → Claude описывает объект → добавляется в промпт
Без добавок → генерация запускается без изменений
```

---

## 4. КОМАНДЫ БОТА

| Команда | Описание | Результат |
|---------|----------|-----------|
| `/start` | Приветствие и список команд | — |
| `/help` | Подробная справка по всем функциям | — |
| `/reference` | Запустить Функцию 1 (по референсу) | 2 PNG |
| `/style` | Запустить Функцию 2 (по стилю) | 3 PNG |
| `/describe` | Запустить Функцию 3 (описать стиль) | 1 PNG |
| `/styles` | Показать описание всех 4 стилей | — |
| `/cancel` | Отменить текущий процесс | — |

---

## 5. ТЕКСТЫ СООБЩЕНИЙ БОТА

### /start
```
Привет! 👋

Я генерирую профессиональные фото белья с помощью NanaBanana Pro.

📋 Доступные команды:
/reference — по референсу
/style — по стилю из каталога (4 стиля)
/describe — описать стиль своими словами
/styles — описание стилей из каталога
/cancel — отменить текущее действие

Подробная инструкция → /help
```

---

### /help
```
📖 Как пользоваться ботом:

────────────────────
🔍 ФУНКЦИЯ 1 — ПО РЕФЕРЕНСУ (/reference)
────────────────────
1. Напиши /reference
2. Пришли любое фото в нужном тебе стиле
3. Я проанализирую кадр и составлю промпт
4. Пришли фото своих трусов
5. Получи готовые изображения (PNG-файлами)

────────────────────
🎨 ФУНКЦИЯ 2 — ПО СТИЛЮ (/style)
────────────────────
1. Напиши /style
2. Пришли фото своих трусов
3. Выбери стиль: 🌸 Нежный / 🌑 Тёмный / 💎 Rich / 🎲 Смешанное
4. Получи 3 изображения в этом стиле

────────────────────
✏️ ФУНКЦИЯ 3 — ОПИСАТЬ СТИЛЬ (/describe)
────────────────────
1. Напиши /describe
2. Опиши желаемый стиль съёмки словами
3. Я составлю промпт по твоему описанию
4. Пришли фото своих трусов → получи изображение

────────────────────
🎁 ДОП. ЭЛЕМЕНТЫ
────────────────────
После каждой загрузки фото трусов бот предложит добавить в кадр:
📇 Визитку · 📖 Журнал INTIMNO · или любой реквизит своими словами / фото

────────────────────
📎 ФОРМАТЫ
────────────────────
Принимаю: фото из галереи или файл (PNG, JPG, JPEG, WEBP)
Отдаю: PNG-файл в полном качестве

────────────────────
⚠️ ВАЖНО
────────────────────
— Без фото трусов генерация не запустится
— Если что-то пошло не так → /cancel и начни заново

По всем вопросам: @oreobra 🙂
```

---

### Меню выбора стиля
```
Выбери стиль (3 изображения):

🌸 Нежный — пастельные тона, мягкий свет, цветы, романтика
🌑 Тёмный — тёмные фоны, контрастный свет, luxury-атмосфера
💎 Rich — белый шёлк, золото, бархат, журнал INTIMNO
🎲 Смешанное — разные стили, неожиданные сочетания

[🌸 Нежный]  [🌑 Тёмный]
[💎 Rich]    [🎲 Смешанное]
```

---

### Меню доп. элементов
```
🎁 Хочешь добавить что-то в кадр?

📇 Визитка — маленькая визитка с брендом INTIMNO
📖 Журнал INTIMNO — журнал с названием бренда
✏️ Описать — любой реквизит своими словами
🖼 Прислать фото — пришли фото реквизита

Или нажми «Без добавок» — и я сразу запущу генерацию.

[📇 Визитка]         [📖 Журнал INTIMNO]
[✏️ Описать словами] [🖼 Прислать фото]
[✅ Без добавок — генерировать]
```

---

### Ожидание генерации
```
⏳ Отправляю в NanaBanana Pro, жди немного...
Обычно занимает 30–60 секунд.
```

---

### Ошибка цензуры
```
🚫 Изображение не прошло через фильтры NanaBanana Pro — сервис его не пропустил.

Попробуй с другим фото или напиши @oreobra
```

---

## 6. СТИЛИ И ПРОМПТЫ

Все промпты: формат 3:4 вертикальный, без людей, только product/flatlay, на выходе PNG 1K.

---

### 🌸 НЕЖНЫЙ (3 промпта)

Характер: пастельные тона, мягкий рассеянный свет, утренняя атмосфера, цветы, сатин, нюдовые фоны, романтика, Instagram/Pinterest женская эстетика.

**Н-1 — Флетлэй на сатине с розами**
```
A 3:4 vertical boudoir flatlay of women's panties from the attached image
neatly arranged on pale milk satin background,
overhead 90-degree angle,
soft diffused window light from behind and a subtle fill from the front,
fresh roses and peonies arranged around,
romantic feminine atmosphere, Instagram boudoir aesthetic,
ultra-realistic 4K quality, very sharp focus so the fabric from the attached panties image
looks extremely high quality and smooth.
Shot on a Canon EOS R5 with a 50mm f/1.2 prime lens, tripod mounted, aperture around f/8, ISO 100.
```

**Н-2 — Флетлэй на постели с розами и пионами**
```
A 3:4 vertical flatlay of women's panties from the attached image
arranged in a light staircase pattern on crisp white bedding,
slightly above at 70 degrees camera angle,
soft diffused window light from behind and a subtle fill from the front,
a bouquet of fresh roses and peonies lightly scattered around,
Pinterest romantic vibe, soft feminine atmosphere,
ultra-realistic 4K quality, detailed texture so the fabric from the attached panties image
looks very high quality.
Shot on a Canon EOS R5 with a 50mm f/1.2 prime lens, tripod mounted, aperture around f/8, ISO 100.
```

**Н-3 — Флетлэй на постели, утренний свет**
```
A 3:4 vertical lifestyle shot of women's panties from the attached image
placed in the center on softly wrinkled white linen bedding,
camera at about 70 degrees for a semi-flatlay depth effect,
soft morning window light from the right at 40 degrees,
a small jewelry dish and tiny dried wildflowers nearby,
dreamy boudoir Instagram vibe,
ultra-detailed 4K quality with precise rendering so the fabric from the attached panties image
looks thick, soft and high quality.
Shot on a Canon EOS R5 with a 50mm f/1.2 L lens at f/8, ISO 100.
```

---

### 🌑 ТЁМНЫЙ (3 промпта)

Характер: тёмные фоны (тёмно-серый, чёрный, уголь), свечи, парфюм, контрастный свет с рим-лайтом, драматика, luxury-атмосфера, вечерний свет.

**Т-1 — Флетлэй на тёмном пушистом фоне**
```
A 3:4 vertical boudoir flatlay of women's panties from the attached image
arranged in a tight fan on soft plush faux fur surface in dark grey tones,
overhead 90-degree angle,
continuous softbox lighting from 45 degrees with dramatic shadows,
a decorative candle with warm flame glow nearby,
high-end editorial Instagram style, moody dark atmosphere,
ultra-detailed 4K quality with precise rendering so the fabric from the attached panties image
looks premium and perfectly rendered.
Shot on a Sony A7 IV with an 85mm f/1.4 prime lens, aperture around f/5.6, ISO 200.
```

**Т-2 — Нюдовая ткань на тёмной поверхности, свеча**
```
A 3:4 vertical boudoir flatlay of women's panties from the attached image
arranged in a diagonal row on silky nude fabric over a dark grey surface,
overhead 90-degree angle,
warm evening light from a nearby lamp, soft dramatic shadows,
a decorative black candle and a luxury perfume bottle placed beside,
moody dark editorial Instagram aesthetic,
ultra-realistic 4K quality with crisp edges and accurate color
so the panties from the attached image look like premium designer lingerie.
Shot on a Sony A7 IV with an 85mm f/1.4 prime lens, aperture around f/5.6, ISO 200.
```

**Т-3 — Lifestyle с чёрным подносом и свечами**
```
A 3:4 vertical editorial lifestyle scene of women's panties from the attached image
arranged in a cascading diagonal fan from top left to bottom right on matte black tray,
slightly above at 70 degrees camera angle,
warm evening light, soft shadows from a nearby lamp,
a perfume bottle and a decorative candle with a warm glowing flame,
luxury dark editorial Instagram aesthetic,
ultra-realistic 4K quality with crisp edges and accurate color
so the panties from the attached image look like premium designer lingerie.
Photographed on a Canon EOS R5 with a 50mm f/1.2 L lens at f/8, ISO 100.
```

---

### 💎 RICH (3 промпта)

Характер: белый шёлк, мрамор, бархат, золотые аксессуары, жемчуг, журнал INTIMNO, роскошная editorial-эстетика, яркий дорогой свет.

**R-1 — Белый шёлковый кимоно, золотой свет, журнал INTIMNO**
```
A 3:4 vertical editorial flatlay of women's panties from the attached image,
arranged in an elegant open fan directly on a white silk kimono
with subtle delicate embroidery, the kimono fabric draped naturally
filling the entire background with soft ivory folds,
camera at about 75 degrees,
bright golden sunlight from the top left at 35 degrees,
warm glowing highlights running across the silk kimono surface
and directly illuminating the fan of panties,
crisp sun-kissed light with long soft shadows following the fabric folds,
a thin gold chain necklace and small pearl earrings
placed organically to the left of the fan,
an open fashion magazine with the title INTIMNO on the cover
placed to the right, slightly angled, pages naturally fanned,
warm feminine Pinterest editorial aesthetic, bright and luxurious,
ultra-realistic 4K quality so the fabric from the attached panties image
looks flawless, premium and perfectly rendered,
every texture detail sharp and true to the original garment.
Shot on a Canon EOS R5 with a 50mm f/1.2 L lens at f/7.1, ISO 100,
tripod mounted, color-calibrated studio-natural hybrid lighting.
```

**R-2 — Белый мрамор, орхидеи, люкс-парфюм, жемчужный браслет**
```
A 3:4 vertical editorial flatlay of women's panties from the attached image
arranged in a neat elegant fan on a cool white marble surface,
camera at about 80 degrees,
soft studio lighting from 45 degrees with subtle warm gold reflectors,
a luxury glass perfume bottle with a gold cap
and a delicate pearl bracelet placed organically beside the panties,
a single spray of fresh white orchid blooms in the upper corner,
high-end fashion editorial aesthetic, crisp and luminous,
ultra-realistic 4K quality so the fabric from the attached panties image
looks flawless, premium and perfectly rendered,
every texture detail sharp and true to the original garment.
Shot on a Canon EOS R5 with a 50mm f/1.2 L lens at f/8, ISO 100, tripod mounted.
```

**R-3 — Слоновая кость, бархат, кристальная шпилька, золочёная книга**
```
A 3:4 vertical editorial lifestyle shot of women's panties from the attached image
arranged in a cascading waterfall fold on ivory velvet fabric,
camera at 70 degrees for a luxurious semi-flatlay perspective,
warm champagne-toned directional lighting from top right at 40 degrees
creating rich golden highlights and soft deep shadows in the velvet texture,
a delicate crystal hair pin and a strand of pearls
loosely draped across the bottom edge of the panties,
an open hardcover book with a gold-embossed spine placed to the left,
refined luxury boudoir aesthetic, warm ivory and gold tones,
ultra-realistic 4K quality so the fabric from the attached panties image
looks exceptionally premium and silky smooth,
every texture detail sharp and true to the original garment.
Shot on a Sony A7 IV with an 85mm f/1.4 prime lens at f/5.6, ISO 100.
```

---

### 🎲 СМЕШАННОЕ (3 промпта)

Характер: неожиданные сочетания объектов, разные фактуры и атмосферы, каждый раз новый результат.

**М-1 — Белый сатин, ноты, ромашки, флакон крема**
```
A 3:4 vertical Pinterest-style product photo of women's panties from the attached image
lying on soft white satin fabric,
shot in bright natural daytime light from a nearby window,
ultra-realistic 4K quality as if taken with a professional camera,
with a partially visible music score book in the top left corner
and a dark brown body cream tube with a white label resting on the book,
a bouquet of daisies placed in the upper right corner,
the panties from the attached image positioned in the center as the main focus
with very high-quality fabric rendering,
and a barely visible necklace in the lower left corner gently exiting the frame,
no text in the scene, Instagram aesthetic.
```

**М-2 — Серый диван, вид сверху, утренний свет**
```
A 3:4 vertical ultra-realistic 4K product photo for a marketplace:
women's panties from the attached image are laid out like a small staircase
on a large soft modern gray sofa,
high-end minimalist interior,
shot from a perfectly straight top-down camera angle,
with a stripe of gentle morning sunlight falling across part of the sofa and panties,
creating soft shadows and a cozy atmosphere,
professional photoshoot look,
very detailed rendering so the fabric from the attached panties image
appears extremely high quality,
no text in the scene.
```

**М-3 — Серый искусственный мех, свеча, белая книга**
```
A 3:4 vertical ultra-realistic 4K product photo:
women's panties from the attached image arranged in an overlapping fan
on a fluffy grey faux-fur blanket lying on white bedding,
top-down angle,
a lit candle in a black jar and a white book edge sit top-right,
warm cozy lighting,
highly detailed fabric rendering,
no text in the scene.
```

---

## 7. ТЕХНИЧЕСКИЙ СТЕК

| Компонент | Технология |
|-----------|-----------|
| Язык | Python 3.11+ |
| Telegram framework | aiogram 3.x (async, FSM) |
| Генерация изображений | `google/nano-banana-pro` via Replicate API |
| Анализ изображений / промпты | `anthropic/claude-4-sonnet` via Replicate API |
| HTTP-клиент | aiohttp |
| Управление состояниями | aiogram MemoryStorage (FSM) |
| Конфигурация | python-dotenv |

### Параметры NanaBanana Pro

| Параметр | Значение |
|----------|----------|
| `aspect_ratio` | `3:4` |
| `resolution` | `1K` |
| `output_format` | `png` |
| `safety_filter_level` | `block_only_high` |
| `image_input` | массив с фото трусов (и опционально доп. фото) |

---

## 8. СТРУКТУРА ПРОЕКТА

```
bot-for-images/
├── bot.py          # Хэндлеры, FSM, запуск
├── config.py       # Переменные окружения
├── states.py       # Состояния FSM
├── prompts.py      # 4 стиля × 3 промпта
├── services.py     # Вызовы Replicate API
├── .env            # Секреты (не коммитить)
├── .env.example    # Шаблон переменных
├── requirements.txt
└── README.md
```

### Машина состояний (State Machine)

```
ReferenceFlow:
  waiting_reference   → ждёт референс-фото
  waiting_panties     → ждёт фото трусов
  choosing_extras     → показано меню доп. элементов
  waiting_extras_text → ждёт текстовое описание реквизита
  waiting_extras_image → ждёт фото реквизита

StyleFlow:
  waiting_panties     → ждёт фото трусов
  choosing_style      → показано меню стилей
  choosing_extras     → показано меню доп. элементов
  waiting_extras_text
  waiting_extras_image

DescribeFlow:
  waiting_description → ждёт текстовое описание стиля
  waiting_panties     → ждёт фото трусов
  choosing_extras     → показано меню доп. элементов
  waiting_extras_text
  waiting_extras_image
```

---

## 9. ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ

```env
TELEGRAM_TOKEN=токен_от_BotFather
REPLICATE_API_TOKEN=токен_от_replicate.com
```

---

## 10. ЗАПУСК

```bash
# Установить зависимости
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Заполнить .env и запустить
python bot.py
```

---

## 11. ТЕСТОВЫЙ ЧЕК-ЛИСТ

- [ ] `/start` выводит приветствие со списком команд
- [ ] `/help` выводит подробную инструкцию со всеми 3 функциями и 4 стилями
- [ ] `/styles` описывает все 4 стиля
- [ ] **Функция 1:** бот не генерирует без фото трусов
- [ ] **Функция 1:** Claude корректно анализирует референс и составляет 2 промпта
- [ ] **Функция 1:** после фото трусов появляется меню доп. элементов
- [ ] **Функция 1:** генерируются 2 PNG-файла
- [ ] **Функция 2:** меню стилей не появляется без фото трусов
- [ ] **Функция 2:** все 4 стиля доступны в меню
- [ ] **Функция 2:** при выборе стиля генерируются 3 PNG-файла
- [ ] **Функция 3:** Claude корректно составляет промпт по текстовому описанию
- [ ] **Функция 3:** генерируется 1 PNG-файл
- [ ] **Доп. элементы:** визитка добавляется к промпту
- [ ] **Доп. элементы:** журнал INTIMNO добавляется к промпту
- [ ] **Доп. элементы:** текстовое описание реквизита добавляется к промпту
- [ ] **Доп. элементы:** фото реквизита анализируется Claude и добавляется к промпту
- [ ] Изображения отдаются как PNG-файлы (не сжатые фото)
- [ ] При ошибке цензуры NanaBanana бот пишет соответствующее сообщение
- [ ] `/cancel` сбрасывает любое состояние
- [ ] Бот принимает изображения как из галереи, так и файлом (PNG, JPG, JPEG, WEBP)

---

*Документ обновлён: апрель 2026*
