import asyncio
import io
import logging

import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BotCommand,
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

import config
import services
from prompts import (
    STYLE_DARK_PROMPTS,
    STYLE_MIXED_PROMPTS,
    STYLE_RICH_PROMPTS,
    STYLE_SOFT_PROMPTS,
)
from states import DescribeFlow, ReferenceFlow, StyleFlow

# ──────────────────────────────────────────────────────────
#  Static texts
# ──────────────────────────────────────────────────────────

START_TEXT = """Привет! 👋

Я генерирую профессиональные фото белья с помощью NanaBanana Pro.

📋 Доступные команды:
/reference — по референсу
/style — по стилю из каталога (4 стиля)
/describe — описать стиль своими словами
/styles — описание стилей из каталога
/cancel — отменить текущее действие

Подробная инструкция → /help"""

HELP_TEXT = """📖 Как пользоваться ботом:

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

По всем вопросам: @oreobra 🙂"""

STYLES_TEXT = """🌸 Нежный — пастельные тона, мягкий свет, цветы, романтика.
Утренняя атмосфера, сатин, нюдовые фоны, Instagram/Pinterest женская эстетика.

🌑 Тёмный — тёмные фоны (тёмно-серый, чёрный, уголь), свечи, парфюм, контрастный свет.
Драматика, luxury-атмосфера, вечерний свет.

💎 Rich — белый шёлк, мрамор, бархат, золотые аксессуары, журнал INTIMNO.
Роскошная editorial-эстетика, яркий и дорогой свет.

🎲 Смешанное — неожиданные сочетания: диван, ноты, ромашки, свечи, текстуры.
Разнообразные атмосферы, каждый раз разный результат."""

NO_PHOTO_TEXT = """⚠️ Для генерации нужно фото твоих трусов.

Пришли изображение — фото из галереи или файл (PNG, JPG, JPEG).
Именно твои трусы будут основой кадра."""

WAITING_TEXT = "⏳ Отправляю в NanaBanana Pro, жди немного...\nОбычно занимает 30–60 секунд."

CENSORED_TEXT = (
    "🚫 Изображение не прошло через фильтры NanaBanana Pro — сервис его не пропустил.\n\n"
    "Попробуй с другим фото или напиши @oreobra"
)

ERROR_TEXT = "❌ Что-то пошло не так при генерации. Попробуй ещё раз или напиши @oreobra"

RESULT_TEXT = "✅ Готово! Вот твоё изображение.\n\nХочешь ещё? /reference, /style или /describe"

STYLE_MENU_TEXT = (
    "Выбери стиль (3 изображения):\n\n"
    "🌸 Нежный — пастельные тона, мягкий свет, цветы, романтика\n"
    "🌑 Тёмный — тёмные фоны, контрастный свет, luxury-атмосфера\n"
    "💎 Rich — белый шёлк, золото, бархат, журнал INTIMNO\n"
    "🎲 Смешанное — разные стили, неожиданные сочетания"
)

EXTRAS_QUESTION_TEXT = (
    "🎁 Хочешь добавить что-то в кадр?\n\n"
    "📇 Визитка — маленькая визитка с брендом INTIMNO\n"
    "📖 Журнал INTIMNO — журнал с названием бренда\n"
    "✏️ Описать — любой реквизит своими словами\n"
    "🖼 Прислать фото — пришли фото реквизита\n\n"
    "Или нажми «Без добавок» — и я сразу запущу генерацию."
)

# MIME types accepted as image files
_IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"}

# ──────────────────────────────────────────────────────────
#  Keyboards
# ──────────────────────────────────────────────────────────

STYLE_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="🌸 Нежный",    callback_data="style_soft"),
            InlineKeyboardButton(text="🌑 Тёмный",    callback_data="style_dark"),
        ],
        [
            InlineKeyboardButton(text="💎 Rich",       callback_data="style_rich"),
            InlineKeyboardButton(text="🎲 Смешанное", callback_data="style_mixed"),
        ],
    ]
)

EXTRAS_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="📇 Визитка", callback_data="extras_card"),
            InlineKeyboardButton(text="📖 Журнал INTIMNO", callback_data="extras_magazine"),
        ],
        [
            InlineKeyboardButton(text="✏️ Описать словами", callback_data="extras_describe"),
            InlineKeyboardButton(text="🖼 Прислать фото", callback_data="extras_photo"),
        ],
        [
            InlineKeyboardButton(text="✅ Без добавок — генерировать", callback_data="extras_skip"),
        ],
    ]
)

# ──────────────────────────────────────────────────────────
#  Filter: photo or image document
# ──────────────────────────────────────────────────────────

_IMAGE_FILTER = F.photo | (F.document & F.document.mime_type.in_(_IMAGE_MIME_TYPES))

# ──────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────

def get_image_file_id(message: Message) -> str | None:
    """Return file_id from a photo or an image document. None otherwise."""
    if message.photo:
        return message.photo[-1].file_id
    if (
        message.document
        and message.document.mime_type
        and message.document.mime_type in _IMAGE_MIME_TYPES
    ):
        return message.document.file_id
    return None


async def download_telegram_file(bot: Bot, file_id: str) -> bytes:
    buf = io.BytesIO()
    file = await bot.get_file(file_id)
    await bot.download_file(file.file_path, destination=buf)
    buf.seek(0)
    return buf.read()


async def download_url_as_bytes(url: str) -> bytes:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            resp.raise_for_status()
            return await resp.read()


async def send_image_as_file(target: Message, image_url: str, caption: str) -> None:
    """Download generated image and send it as a PNG document (full quality, no Telegram compression)."""
    image_bytes = await download_url_as_bytes(image_url)
    doc = BufferedInputFile(image_bytes, filename="generated.png")
    await target.answer_document(document=doc, caption=caption)


async def show_extras_menu(
    message: Message,
    state: FSMContext,
    flow: str,
    panties_file_id: str,
    prompts: list[str],
    style_name: str = "",
) -> None:
    """
    Save generation data to state and show the extras selection menu.
    Called after panties photo is received in any flow.
    """
    _extras_state = {
        "reference": ReferenceFlow.choosing_extras,
        "style":     StyleFlow.choosing_extras,
        "describe":  DescribeFlow.choosing_extras,
    }
    await state.update_data(
        flow=flow,
        panties_file_id=panties_file_id,
        prompts=prompts,
        style_name=style_name,
    )
    await state.set_state(_extras_state[flow])
    await message.answer(EXTRAS_QUESTION_TEXT, reply_markup=EXTRAS_KEYBOARD)


async def run_generation(
    target: Message,
    bot: Bot,
    state: FSMContext,
    extras: str | None = None,
) -> None:
    """
    Central generation runner. Reads state data, applies optional extras,
    runs all prompts in parallel, and sends results as PNG files.
    """
    data = await state.get_data()
    panties_file_id: str = data["panties_file_id"]
    base_prompts: list[str] = data["prompts"]
    style_name: str = data.get("style_name", "")
    total = len(base_prompts)

    gen_msg = await target.answer(WAITING_TEXT)

    # Append extras text to each prompt if provided
    prompts = (
        [f"{p}, {extras}" for p in base_prompts]
        if extras
        else base_prompts
    )

    try:
        panties_bytes = await download_telegram_file(bot, panties_file_id)
        tasks = [services.generate_image(p, panties_bytes) for p in prompts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        await gen_msg.delete()

        success = 0
        for idx, result in enumerate(results, start=1):
            if isinstance(result, services.CensorshipError):
                await target.answer(
                    f"🚫 Вариант {idx}/{total}: не прошло фильтры NanaBanana Pro."
                )
            elif isinstance(result, Exception):
                logging.error("Generation %d/%d failed: %s", idx, total, result)
                await target.answer(f"❌ Вариант {idx}/{total}: ошибка генерации.")
            elif result:
                if total == 1:
                    caption = RESULT_TEXT
                else:
                    prefix = f"{style_name} — " if style_name else ""
                    caption = f"✅ {prefix}вариант {idx}/{total}"
                await send_image_as_file(target, result, caption)
                success += 1

        if success == 0:
            await target.answer(ERROR_TEXT)
        elif total > 1 and success == total:
            await target.answer(
                f"✅ Все {total} варианта готовы!\n\nХочешь ещё? /reference, /style или /describe"
            )
        elif total > 1 and success < total:
            await target.answer(
                f"Готово! Получилось {success} из {total}.\n\nХочешь ещё? /reference, /style или /describe"
            )
        # total==1 success==1: caption on the document is enough

    except Exception as exc:
        logging.error("run_generation failed: %s", exc)
        try:
            await gen_msg.delete()
        except Exception:
            pass
        await target.answer(ERROR_TEXT)
    finally:
        await state.clear()


# ──────────────────────────────────────────────────────────
#  Command handlers
# ──────────────────────────────────────────────────────────

async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(START_TEXT)


async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)


async def cmd_styles(message: Message) -> None:
    await message.answer(STYLES_TEXT)


async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("✅ Отменено. Начни заново: /reference, /style или /describe")


async def cmd_reference(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(ReferenceFlow.waiting_reference)
    await message.answer(
        "🔍 Пришли любое фото в нужном тебе стиле — с Pinterest, из интернета или свой референс.\n\n"
        "Можно фото из галереи или файлом (PNG, JPG, JPEG).\n\n"
        "Я проанализирую стиль, составлю промпт и запущу генерацию."
    )


async def cmd_style(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(StyleFlow.waiting_panties)
    await message.answer(
        "🎨 Пришли фото своих трусов — и я предложу выбрать стиль.\n\n"
        "Можно фото из галереи или файлом (PNG, JPG, JPEG)."
    )


async def cmd_describe(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(DescribeFlow.waiting_description)
    await message.answer(
        "✏️ Опиши желаемый стиль съёмки своими словами.\n\n"
        "Например: «нежный стиль, лепестки роз, утренний свет, белое постельное бельё»\n"
        "или «тёмный люкс, свечи, контрастный свет, тёмная поверхность»\n\n"
        "Описание может быть на русском или английском."
    )


# ──────────────────────────────────────────────────────────
#  Function 1 — Reference flow
# ──────────────────────────────────────────────────────────

async def ref_got_reference(message: Message, state: FSMContext) -> None:
    """State: waiting_reference — user sent reference image."""
    file_id = get_image_file_id(message)
    if not file_id:
        await message.answer(
            "Мне нужно изображение, не текст.\n"
            "Пришли фото из галереи или файл (PNG, JPG, JPEG)."
        )
        return

    analyzing_msg = await message.answer("🔍 Анализирую референс, составляю промпты...")

    try:
        image_bytes = await download_telegram_file(message.bot, file_id)
        p1, p2 = await services.analyze_reference_double(image_bytes)

        await analyzing_msg.delete()
        await message.answer(
            f"✅ Промпты по твоему референсу:\n\n"
            f"<b>Вариант 1:</b>\n<code>{p1}</code>\n\n"
            f"<b>Вариант 2:</b>\n<code>{p2}</code>\n\n"
            "Теперь пришли фото своих трусов — запущу оба варианта.\n"
            "Можно фото из галереи или файлом.",
            parse_mode="HTML",
        )
        await state.update_data(prompts=[p1, p2], style_name="")
        await state.set_state(ReferenceFlow.waiting_panties)

    except Exception as exc:
        logging.error("Reference analysis failed: %s", exc)
        await analyzing_msg.delete()
        await message.answer(ERROR_TEXT)
        await state.clear()


async def ref_got_panties(message: Message, state: FSMContext) -> None:
    """State: waiting_panties (Function 1) — user sent panties image."""
    file_id = get_image_file_id(message)
    if not file_id:
        await message.answer(
            "Мне нужно фото трусов.\n"
            "Пришли фото из галереи или файл (PNG, JPG, JPEG)."
        )
        return

    data = await state.get_data()
    prompts = data.get("prompts", [])
    if not prompts:
        await message.answer("Что-то пошло не так. Начни заново: /reference")
        await state.clear()
        return

    await show_extras_menu(message, state, "reference", file_id, prompts, style_name="")


# ──────────────────────────────────────────────────────────
#  Function 2 — Style flow
# ──────────────────────────────────────────────────────────

async def style_got_panties(message: Message, state: FSMContext) -> None:
    """State: waiting_panties (Function 2) — user sent panties image."""
    file_id = get_image_file_id(message)
    if not file_id:
        await message.answer(NO_PHOTO_TEXT)
        return

    await state.update_data(panties_file_id=file_id)
    await state.set_state(StyleFlow.choosing_style)
    await message.answer(STYLE_MENU_TEXT, reply_markup=STYLE_KEYBOARD)


async def style_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    """Callback: user tapped 🌸 Нежный or 🌑 Тёмный."""
    current = await state.get_state()
    if current != StyleFlow.choosing_style:
        await callback.answer("Сначала пришли фото трусов через /style", show_alert=True)
        return

    data = await state.get_data()
    panties_file_id = data.get("panties_file_id")
    if not panties_file_id:
        await callback.answer("Сначала пришли фото трусов 🙏", show_alert=True)
        await state.clear()
        return

    _prompts_map = {
        "style_soft":  (STYLE_SOFT_PROMPTS,  "🌸 Нежный"),
        "style_dark":  (STYLE_DARK_PROMPTS,  "🌑 Тёмный"),
        "style_rich":  (STYLE_RICH_PROMPTS,  "💎 Rich"),
        "style_mixed": (STYLE_MIXED_PROMPTS, "🎲 Смешанное"),
    }
    prompts, style_name = _prompts_map[callback.data]

    await callback.message.edit_text(f"✅ Стиль выбран: {style_name}")
    await callback.answer()

    await show_extras_menu(
        callback.message, state,
        flow="style",
        panties_file_id=panties_file_id,
        prompts=list(prompts),
        style_name=style_name,
    )


# ──────────────────────────────────────────────────────────
#  Function 3 — Describe flow
# ──────────────────────────────────────────────────────────

async def describe_got_description(message: Message, state: FSMContext) -> None:
    """State: waiting_description — user sent text style description."""
    if not message.text or not message.text.strip():
        await message.answer("Напиши описание стиля текстом, пожалуйста.")
        return

    analyzing_msg = await message.answer("🎨 Создаю промпт по твоему описанию...")

    try:
        prompt = await services.describe_to_prompt(message.text.strip())

        await analyzing_msg.delete()
        await message.answer(
            f"✅ Промпт по твоему описанию:\n\n<code>{prompt}</code>\n\n"
            "Теперь пришли фото своих трусов — и я запущу генерацию.\n"
            "Можно фото из галереи или файлом.",
            parse_mode="HTML",
        )
        await state.update_data(prompts=[prompt], style_name="")
        await state.set_state(DescribeFlow.waiting_panties)

    except Exception as exc:
        logging.error("Description analysis failed: %s", exc)
        await analyzing_msg.delete()
        await message.answer(ERROR_TEXT)
        await state.clear()


async def describe_got_panties(message: Message, state: FSMContext) -> None:
    """State: waiting_panties (Function 3) — user sent panties image."""
    file_id = get_image_file_id(message)
    if not file_id:
        await message.answer(
            "Мне нужно фото трусов.\n"
            "Пришли фото из галереи или файл (PNG, JPG, JPEG)."
        )
        return

    data = await state.get_data()
    prompts = data.get("prompts", [])
    if not prompts:
        await message.answer("Что-то пошло не так. Начни заново: /describe")
        await state.clear()
        return

    await show_extras_menu(message, state, "describe", file_id, prompts, style_name="")


# ──────────────────────────────────────────────────────────
#  Extras handlers (shared across all flows)
# ──────────────────────────────────────────────────────────

_EXTRAS_TEXT_STATES = StateFilter(
    ReferenceFlow.waiting_extras_text,
    StyleFlow.waiting_extras_text,
    DescribeFlow.waiting_extras_text,
)

_EXTRAS_IMAGE_STATES = StateFilter(
    ReferenceFlow.waiting_extras_image,
    StyleFlow.waiting_extras_image,
    DescribeFlow.waiting_extras_image,
)

_CHOOSING_EXTRAS_STATES = StateFilter(
    ReferenceFlow.choosing_extras,
    StyleFlow.choosing_extras,
    DescribeFlow.choosing_extras,
)


async def extras_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    """Callback: user picked an extras option from the menu."""
    choice = callback.data
    data = await state.get_data()
    flow = data.get("flow", "reference")

    _text_state = {
        "reference": ReferenceFlow.waiting_extras_text,
        "style":     StyleFlow.waiting_extras_text,
        "describe":  DescribeFlow.waiting_extras_text,
    }
    _image_state = {
        "reference": ReferenceFlow.waiting_extras_image,
        "style":     StyleFlow.waiting_extras_image,
        "describe":  DescribeFlow.waiting_extras_image,
    }

    if choice == "extras_card":
        extras = "a small elegant business card with brand name INTIMNO placed beside"
        await callback.message.edit_text("📇 Добавляю визитку INTIMNO — запускаю!")
        await callback.answer()
        await run_generation(callback.message, callback.bot, state, extras)

    elif choice == "extras_magazine":
        extras = "an INTIMNO brand magazine placed beside"
        await callback.message.edit_text("📖 Добавляю журнал INTIMNO — запускаю!")
        await callback.answer()
        await run_generation(callback.message, callback.bot, state, extras)

    elif choice == "extras_describe":
        await callback.message.edit_text(
            "✏️ Опиши, что хочешь добавить в кадр:\n\n"
            "Например: «кольцо», «флакон духов», «засушенные цветы», «визитка с логотипом»"
        )
        await state.set_state(_text_state[flow])
        await callback.answer()

    elif choice == "extras_photo":
        await callback.message.edit_text(
            "🖼 Пришли фото реквизита, который хочешь добавить в кадр.\n\n"
            "Например: визитка, упаковка, украшение, свеча и т.д."
        )
        await state.set_state(_image_state[flow])
        await callback.answer()

    elif choice == "extras_skip":
        await callback.message.edit_text("✅ Без добавок — запускаю!")
        await callback.answer()
        await run_generation(callback.message, callback.bot, state, None)


async def extras_got_text(message: Message, state: FSMContext) -> None:
    """User typed the extras description."""
    text = message.text.strip() if message.text else ""
    if not text:
        await message.answer("Напиши, что добавить в кадр.")
        return

    extras = f"with {text} placed in the composition"
    await message.answer(f"✅ Добавляю: «{text}»")
    await run_generation(message, message.bot, state, extras)


async def extras_got_image(message: Message, state: FSMContext) -> None:
    """User sent a photo of the extras prop."""
    file_id = get_image_file_id(message)
    if not file_id:
        await message.answer(
            "Нужно изображение, не текст.\n"
            "Пришли фото реквизита или /cancel для отмены."
        )
        return

    analyzing_msg = await message.answer("🔍 Анализирую реквизит...")

    try:
        image_bytes = await download_telegram_file(message.bot, file_id)
        description = await services.analyze_extras_image(image_bytes)
        extras = f"with {description} placed in the composition"

        await analyzing_msg.delete()
        await message.answer(f"✅ Добавляю: «{description}»")
        await run_generation(message, message.bot, state, extras)

    except Exception as exc:
        logging.error("Extras image analysis failed: %s", exc)
        await analyzing_msg.delete()
        await message.answer(ERROR_TEXT)
        await state.clear()


async def extras_image_got_text(message: Message) -> None:
    """Fallback: text received while waiting for extras image."""
    await message.answer(
        "Мне нужно изображение, не текст.\n"
        "Пришли фото реквизита или /cancel для отмены."
    )


async def extras_unexpected(message: Message) -> None:
    """Fallback: unexpected input while showing extras menu."""
    await message.answer(
        "Выбери вариант из меню выше или нажми /cancel для отмены."
    )


# ──────────────────────────────────────────────────────────
#  Fallback handlers (no active flow)
# ──────────────────────────────────────────────────────────

async def describe_unexpected_image(message: Message) -> None:
    """Image received while waiting for text description."""
    await message.answer(
        "Мне нужен текст, не изображение.\n"
        "Опиши желаемый стиль съёмки словами."
    )


async def fallback_unexpected_image(message: Message) -> None:
    """Image received outside any active flow."""
    await message.answer(
        "Не знаю, что делать с этим изображением 🤔\n\n"
        "Начни через /reference, /style или /describe"
    )


async def fallback_unexpected_text(message: Message, state: FSMContext) -> None:
    """Text received outside any active flow or when image expected."""
    current = await state.get_state()
    if current in (
        ReferenceFlow.waiting_panties,
        StyleFlow.waiting_panties,
        DescribeFlow.waiting_panties,
        ReferenceFlow.waiting_reference,
    ):
        await message.answer(
            "Мне нужно изображение, не текст.\n"
            "Пришли фото из галереи или файл (PNG, JPG, JPEG)."
        )
    else:
        await message.answer(
            "Я понимаю команды и изображения.\n\n"
            "Используй /reference, /style или /describe для начала."
        )


# ──────────────────────────────────────────────────────────
#  Commands menu (visible in Telegram UI)
# ──────────────────────────────────────────────────────────

async def set_commands(bot: Bot) -> None:
    await bot.set_my_commands([
        BotCommand(command="start",    description="Начать работу / краткая инструкция"),
        BotCommand(command="help",     description="Подробная справка"),
        BotCommand(command="reference", description="Генерация по референсу"),
        BotCommand(command="style",    description="Генерация по стилю (4 стиля, 3 фото)"),
        BotCommand(command="describe", description="Описать стиль словами"),
        BotCommand(command="styles",   description="Описание стилей"),
        BotCommand(command="cancel",   description="Отменить текущее действие"),
    ])


# ──────────────────────────────────────────────────────────
#  Router registration
# ──────────────────────────────────────────────────────────

def register_handlers(dp: Dispatcher) -> None:
    # ── Commands ──────────────────────────────────────────
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_styles, Command("styles"))
    dp.message.register(cmd_cancel, Command("cancel"))
    dp.message.register(cmd_reference, Command("reference"))
    dp.message.register(cmd_style, Command("style"))
    dp.message.register(cmd_describe, Command("describe"))

    # ── Function 1 — Reference flow ───────────────────────
    dp.message.register(ref_got_reference, ReferenceFlow.waiting_reference, _IMAGE_FILTER)
    dp.message.register(ref_got_reference, ReferenceFlow.waiting_reference)
    dp.message.register(ref_got_panties,   ReferenceFlow.waiting_panties,   _IMAGE_FILTER)
    dp.message.register(ref_got_panties,   ReferenceFlow.waiting_panties)

    # ── Function 2 — Style flow ────────────────────────────
    dp.message.register(style_got_panties, StyleFlow.waiting_panties, _IMAGE_FILTER)
    dp.message.register(style_got_panties, StyleFlow.waiting_panties)
    dp.callback_query.register(
        style_chosen,
        F.data.in_({"style_soft", "style_dark", "style_rich", "style_mixed"}),
    )

    # ── Function 3 — Describe flow ─────────────────────────
    dp.message.register(describe_got_description, DescribeFlow.waiting_description, F.text)
    dp.message.register(describe_unexpected_image, DescribeFlow.waiting_description, _IMAGE_FILTER)
    dp.message.register(describe_got_panties, DescribeFlow.waiting_panties, _IMAGE_FILTER)
    dp.message.register(describe_got_panties, DescribeFlow.waiting_panties)

    # ── Extras (shared across all flows) ──────────────────
    dp.callback_query.register(
        extras_chosen,
        F.data.startswith("extras_"),
        _CHOOSING_EXTRAS_STATES,
    )
    dp.message.register(extras_got_text,  _EXTRAS_TEXT_STATES,  F.text)
    dp.message.register(extras_got_image, _EXTRAS_IMAGE_STATES, _IMAGE_FILTER)
    dp.message.register(extras_image_got_text, _EXTRAS_IMAGE_STATES, F.text)
    dp.message.register(extras_unexpected, _CHOOSING_EXTRAS_STATES)

    # ── Fallbacks (must come last) ─────────────────────────
    dp.message.register(fallback_unexpected_image, _IMAGE_FILTER)
    dp.message.register(fallback_unexpected_text)


# ──────────────────────────────────────────────────────────
#  Entry point
# ──────────────────────────────────────────────────────────

async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    )

    bot = Bot(token=config.TELEGRAM_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    register_handlers(dp)

    await set_commands(bot)
    logging.info("NanaBanana bot starting…")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
