# Прототип Telegram-бота для генерации изображений через NanoBanana Pro

> Версия: 1.0 — апрель 2026  
> Контакт для вопросов: @oreobra

---

## 1. ЧТО ДЕЛАЕТ БОТ

Бот помогает генерировать профессиональные изображения женского белья (трусы) через NanaBanana Pro. Он умеет анализировать референсы, составлять промпты и запускать генерации — с реальным изображением трусов как основой. Без исходника генерация не запускается.

---

## 2. ФУНКЦИИ БОТА

### Функция 1 — «По референсу»
Пользователь присылает любое понравившееся изображение → бот анализирует его стиль, угол, свет, фон, настроение → составляет промпт в этом стиле → просит прислать фото трусов → запускает генерацию в NanaBanana Pro → возвращает результат.

### Функция 2 — «По стилю»
Пользователь присылает фото трусов → выбирает стиль из меню (🌸 Нежный / 🌑 Тёмный) → бот прогоняет 5 готовых промптов этого стиля с изображением трусов через NanaBanana Pro → отправляет 5 готовых изображений.

---

## 3. ЛОГИКА И СЦЕНАРИИ (FLOWS)

### Flow 1 — По референсу

```
Пользователь → присылает референс-изображение
     ↓
Бот анализирует: угол, свет, фон, пропсы, настроение, тип кадра
     ↓
Бот составляет промпт по структуре из инструкции
     ↓
Бот отправляет промпт пользователю + просит прислать фото трусов
     ↓
Пользователь → присылает изображение трусов
     ↓
Бот проверяет: изображение получено? → если нет → "Пожалуйста, пришли фото трусов"
     ↓
Бот отправляет [промпт + изображение трусов] в NanaBanana Pro
     ↓
Бот возвращает готовое изображение пользователю
```

**Важно:** бот не запускает генерацию, пока не получил изображение трусов. Это жёсткое условие.

---

### Flow 2 — По стилю

```
Пользователь → присылает фото трусов
     ↓
Бот проверяет: изображение получено? → если нет → "Сначала пришли фото трусов"
     ↓
Бот показывает меню стилей:
     [🌸 Нежный]  [🌑 Тёмный]
     ↓
Пользователь выбирает стиль
     ↓
Бот запускает 5 промптов этого стиля параллельно в NanaBanana Pro
(каждый промпт идёт вместе с изображением трусов)
     ↓
Бот отправляет 5 изображений пользователю (по мере готовности или пачкой)
```

---

## 4. КОМАНДЫ БОТА

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие и краткая инструкция |
| `/help` | Подробная справка: как пользоваться |
| `/reference` | Запустить Функцию 1 (по референсу) |
| `/style` | Запустить Функцию 2 (по стилю) |
| `/styles` | Показать описание стилей |
| `/cancel` | Отменить текущий процесс |

---

## 5. ТЕКСТЫ СООБЩЕНИЙ БОТА

### /start
```
Привет! 👋

Я помогаю генерировать профессиональные изображения твоего белья через NanaBanana Pro.

У меня есть две функции:

🔍 /reference — ты присылаешь референс (любое понравившееся фото), 
я анализирую стиль и создаю похожее изображение с твоими трусами.

🎨 /style — ты присылаешь фото трусов, 
выбираешь стиль, я генерирую 5 изображений сразу.

Для всех генераций нужно фото твоих трусов — именно они будут в кадре.

Если что-то не понятно → /help или напиши @oreobra
```

---

### /help
```
📖 Как пользоваться ботом:

──────────────────────
🔍 ФУНКЦИЯ 1 — ПО РЕФЕРЕНСУ
──────────────────────
1. Напиши /reference
2. Пришли любое фото в нужном тебе стиле (с Pinterest, из интернета, свой референс)
3. Я проанализирую кадр и предложу промпт
4. Пришли фото своих трусов
5. Получи готовое изображение

──────────────────────
🎨 ФУНКЦИЯ 2 — ПО СТИЛЮ
──────────────────────
1. Напиши /style
2. Пришли фото своих трусов
3. Выбери стиль: 🌸 Нежный или 🌑 Тёмный
4. Получи 5 изображений в этом стиле

──────────────────────
⚠️ ВАЖНО
──────────────────────
— Без фото трусов генерация не запустится
— Фото должно быть чётким, хорошего качества
— Если что-то пошло не так → /cancel и начни заново

Остались вопросы? Пиши @oreobra — расскажу всё подробно 🙂
```

---

### Сообщение: изображение не прислано
```
⚠️ Для генерации нужно фото твоих трусов.

Пожалуйста, пришли изображение — я не могу запустить генерацию без исходника. 
Именно твои трусы будут основой кадра.
```

---

### Сообщение: ожидание генерации
```
⏳ Отправляю в NanaBanana Pro, жди немного...
Обычно занимает 30–60 секунд.
```

---

### Сообщение: выбор стиля
```
Выбери стиль:

🌸 Нежный — пастельные тона, мягкий свет, цветы, романтика
🌑 Тёмный — тёмные фоны, контрастный свет, luxury-атмосфера

[🌸 Нежный]    [🌑 Тёмный]
```

---

### Сообщение: результат готов
```
✅ Готово! Вот твоё изображение:
[изображение]

Хочешь ещё? Используй /reference или /style
```

---

## 6. ПРОМПТЫ — СТИЛЬ 🌸 НЕЖНЫЙ

Характер стиля: пастельные и нейтральные тона, мягкий рассеянный свет, утренняя атмосфера, цветы, сатин, нюдовые фоны, романтика, Instagram/Pinterest женская эстетика.

---

### Промпт Н-1 — Флетлэй на сатине с розами

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

---

### Промпт Н-2 — Флетлэй на постели с розами и пионами

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

---

### Промпт Н-3 — Флетлэй на постели, утренний свет

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

### Промпт Н-4 — Outdoor lifestyle, золотой час, дикие цветы

```
A 3:4 vertical lifestyle shot of women's panties from the attached image
placed in the center on pale lightly textured surface,
camera at about 60 degrees for a semi-flatlay depth effect,
golden-hour sunlight from the top left at 35 degrees creating glowing highlights and long soft shadows,
tiny dried wildflowers and baby's breath arranged around,
warm Pinterest mood, romantic cottagecore Pinterest mood,
ultra-detailed 4K quality with precise rendering so the fabric from the attached panties image 
looks thick, soft and high quality.
Captured on a Sony A7 IV with an 85mm f/1.4 prime lens, aperture around f/4, ISO 100.
```

---

### Промпт Н-5 — Флетлэй с парфюмом на нюдовой ткани

```
A 3:4 vertical flatlay of women's panties from the attached image
arranged in a soft staircase on flowing nude-colored fabric,
camera at about 60 degrees for a semi-flatlay depth effect,
warm diffused light from the top,
a perfume bottle and a small jewelry dish for balance,
Pinterest romantic vibe, soft feminine atmosphere,
ultra-realistic 4K quality so the fabric from the attached panties image 
looks very high-end and textured.
Captured on a Sony A7 IV with an 85mm f/1.4 prime lens, aperture around f/4 
for gentle background blur, ISO 100.
```

---

## 7. ПРОМПТЫ — СТИЛЬ 🌑 ТЁМНЫЙ

Характер стиля: тёмные фоны (тёмно-серый, чёрный, уголь), свечи, парфюм, контрастный свет с рим-лайтом, драматика, luxury-атмосфера, вечерний свет.

---

### Промпт Т-1 — Флетлэй на тёмном пушистом фоне

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

---

### Промпт Т-2 — Флетлэй, нюдовая ткань на тёмной поверхности, свеча

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

---

### Промпт Т-3 — Lifestyle с чёрным подносом и свечами

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

### Промпт Т-4 — Каталог, тёмная полированная поверхность, luxury

```
A 3:4 vertical catalog-style product photo of women's panties from the attached image
arranged in a loose fan on dark grey polished surface,
slightly above at 70 degrees camera angle,
studio color-calibrated lighting from 45 degrees with deep dramatic shadows,
a small jewelry dish for balance,
luxury e-commerce aesthetic, high-end editorial Instagram style,
ultra-detailed 4K quality with precise rendering so the fabric from the attached panties image 
looks premium and perfectly rendered.
Photographed on a Canon EOS R5 with a 50mm f/1.2 L lens at f/8, ISO 100.
```

---

### Промпт Т-5 — Luxury product shot, тёмная поверхность

```
A 3:4 vertical high-contrast studio product shot of women's panties from the attached image
placed in the center on dark grey polished surface,
straight overhead angle,
dramatic directional lighting from 45 degrees, deep shadow areas creating luxury depth and contrast,
a luxury perfume bottle and a black decorative candle placed to the side,
luxury beauty-campaign vibe, dark editorial Instagram aesthetic,
ultra-realistic 4K quality with crisp edges and accurate color 
so the panties from the attached image look like premium designer lingerie.
Shot on a Sony A7 IV with an 85mm f/1.4 prime lens, aperture around f/5.6, ISO 200.
```

---

## 8. ИНСТРУКЦИЯ — СОЗДАНИЕ БОТА В ANTIGRAVITY С CLAUDE OPUS 4

### Шаг 1 — Создай нового бота в Telegram

1. Открой @BotFather в Telegram
2. Напиши `/newbot`
3. Придумай имя бота (например: `NanaBanana Studio`)
4. Придумай юзернейм (например: `@nanabanana_studio_bot`)
5. Сохрани выданный **API Token** — он понадобится при подключении в Antigravity

---

### Шаг 2 — Создай проект в Antigravity

1. Зайди в Antigravity и создай новый проект / агент
2. Выбери Telegram как канал подключения
3. Вставь токен от BotFather
4. Выбери модель: **Claude Opus 4** (`claude-opus-4`)

---

### Шаг 3 — Системный промпт для Claude Opus 4

Вставь следующий текст как **System Prompt** агента:

```
You are an assistant inside a Telegram bot that helps generate professional lingerie (panties) product images via NanaBanana Pro.

Your role:
1. Analyze reference images sent by users to understand shooting style, angle, lighting, mood, props, and background.
2. Compose image generation prompts following the exact structure described below.
3. Guide users step by step: ask for reference, create prompt, ask for panties image, trigger generation.
4. Never trigger a generation without the panties source image — this is a strict rule.
5. Always respond in the language the user writes in (Russian or English).

---

PROMPT STRUCTURE — FLATLAY / PRODUCT SHOTS ONLY:
A 3:4 vertical [shot type] of women's panties from the attached image
[arrangement] on [surface/background], [camera angle],
[lighting direction + type + angle], [props if needed],
[mood/aesthetic],
ultra-realistic 4K quality [fabric quality formula].
[Camera settings if needed].

RULES:
- Format is always 3:4 vertical — never change this
- All prompts are product/flatlay only — no model shots
- Fabric quality formula is mandatory in every prompt
- Prompts must be written in English
- Always reference the panties image with "from the attached image"

---

CONVERSATION FLOW FOR FUNCTION 1 (Reference):
Step 1: User sends reference image → analyze it, compose prompt, show it to user
Step 2: Ask user to send their panties image
Step 3: Wait for panties image — do NOT generate without it
Step 4: Trigger NanaBanana generation with [prompt + panties image]
Step 5: Return result

CONVERSATION FLOW FOR FUNCTION 2 (Style):
Step 1: Ask user to send their panties image
Step 2: Wait for panties image — do NOT show style menu without it
Step 3: Show style menu: 🌸 Нежный / 🌑 Тёмный
Step 4: Run all 5 prompts of chosen style with panties image through NanaBanana
Step 5: Return 5 images

---

ERROR HANDLING:
- If user tries to choose style without sending panties image: "Сначала пришли фото трусов 🙏"
- If user sends text when photo is expected: "Мне нужно изображение, не текст. Пришли фото, пожалуйста."
- If generation fails: "Что-то пошло не так при генерации. Попробуй ещё раз или напиши @oreobra"

CONTACT: For any questions users can't solve, direct them to @oreobra
```

---

### Шаг 4 — Настройка команд бота

В Antigravity добавь обработку следующих команд:

| Команда | Действие |
|---------|----------|
| `/start` | Отправить приветственное сообщение (текст из раздела 5) |
| `/help` | Отправить подробную инструкцию (текст из раздела 5) |
| `/reference` | Установить состояние: ожидание референс-изображения |
| `/style` | Установить состояние: ожидание изображения трусов → затем показ меню стилей |
| `/styles` | Отправить описание двух стилей |
| `/cancel` | Сбросить текущее состояние, отправить: «Отменено. Начни заново: /reference или /style» |

---

### Шаг 5 — Подключение NanaBanana Pro

1. Получи API ключ NanaBanana Pro
2. В Antigravity добавь **Action/Tool** типа «HTTP Request» или «API Call»
3. Настрой вызов:
   - URL: `[NanaBanana API endpoint]`
   - Method: POST
   - Body: `{ "prompt": "[текст промпта]", "image": "[base64 или URL изображения трусов]" }`
4. На выходе Action возвращает URL или base64 сгенерированного изображения
5. Это изображение бот отправляет пользователю через Telegram

> 📌 Уточни у NanaBanana Pro их актуальную документацию по API — endpoint и формат тела запроса могут отличаться.

---

### Шаг 6 — Хранение промптов стилей

В Antigravity создай **Knowledge Base** или **Variables** с двумя наборами промптов:

**Переменная: `STYLE_SOFT`** — массив из 5 промптов стиля 🌸 Нежный (промпты Н-1 … Н-5 из раздела 6)

**Переменная: `STYLE_DARK`** — массив из 5 промптов стиля 🌑 Тёмный (промпты Т-1 … Т-5 из раздела 7)

При запуске Функции 2 бот итерирует по массиву выбранного стиля и для каждого промпта делает отдельный вызов к NanaBanana.

---

### Шаг 7 — Управление состояниями (State Machine)

Бот должен отслеживать, на каком шаге находится пользователь:

```
state: idle          → ждёт команду
state: ref_waiting   → ждёт референс-изображение (Функция 1)
state: panties_f1    → ждёт изображение трусов (Функция 1, после получения промпта)
state: panties_f2    → ждёт изображение трусов (Функция 2)
state: style_choice  → показано меню стилей, ждёт выбор
state: generating    → идёт генерация, блокирует новые запросы
```

При каждом состоянии бот должен корректно реагировать на неожиданный ввод:
- Получил текст, когда ждёт фото → просит прислать фото
- Получил фото, когда ждёт текст/выбор → уточняет, что именно нужно сделать

---

## 9. ТЕСТОВЫЙ СЦЕНАРИЙ (ЧЕК-ЛИСТ)

Перед запуском проверь:

- [ ] `/start` работает и выводит приветствие
- [ ] `/help` выводит подробную инструкцию
- [ ] Функция 1: бот не генерирует без изображения трусов
- [ ] Функция 1: бот корректно анализирует референс и составляет промпт
- [ ] Функция 1: генерация запускается после получения изображения трусов
- [ ] Функция 2: меню стилей не появляется без изображения трусов
- [ ] Функция 2: при выборе стиля генерируются все 5 изображений
- [ ] При ошибке генерации бот пишет сообщение об ошибке с контактом @oreobra
- [ ] `/cancel` корректно сбрасывает состояние
- [ ] Все промпты переданы в NanaBanana вместе с изображением трусов

---

*Документ подготовлен: апрель 2026*
