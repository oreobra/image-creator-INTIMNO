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
import notes
import services
from states import DescribeFlow, FeedbackFlow, ReferenceFlow

# ──────────────────────────────────────────────────────────
#  Static texts
# ──────────────────────────────────────────────────────────

START_TEXT = """Привет! 👋

Я генерирую профессиональные фото белья с помощью Nanobanana Pro.

📋 Доступные команды:
/reference — по референсу
/describe — описать стиль своими словами
/cancel — отменить текущее действие

Подробная инструкция → /help"""

HELP_TEXT = """📖 Как пользоваться ботом:

────────────────────
🔍 ФУНКЦИЯ 1 — ПО РЕФЕРЕНСУ (/reference)
────────────────────
1. Напиши /reference
2. Пришли фото своих трусов (одно или несколько — например, спереди и сзади), затем нажми «Готово»
3. Я определю материал и цвет
4. Пришли любое фото в нужном тебе стиле
5. Я составлю промпт, учитывая материал/цвет трусов и референс
6. Получи готовые изображения (PNG-файлами)

────────────────────
✏️ ФУНКЦИЯ 2 — ОПИСАТЬ СТИЛЬ (/describe)
────────────────────
1. Напиши /describe
2. Пришли фото своих трусов (одно или несколько), затем нажми «Готово»
3. Я определю материал и цвет
4. Опиши желаемый стиль съёмки словами
5. Я составлю промпт с учётом материала/цвета трусов → получи изображение

────────────────────
🎁 ДОП. ЭЛЕМЕНТЫ
────────────────────
После составления промпта бот предложит добавить в кадр:
📇 Визитку · 📖 Журнал INTIMNO · или любой реквизит своими словами / фото

────────────────────
💬 ОБРАТНАЯ СВЯЗЬ
────────────────────
После генерации бот спросит, как тебе результат. Фидбэк помогает боту
подбирать более удачные сочетания в следующий раз.

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

PANTIES_REQUEST_TEXT = (
    "👙 Для начала пришли фото своих трусов — можно одно или несколько (например, спереди и сзади).\n\n"
    "Когда загрузишь все, нажми «Готово». Я определю материал и цвет — это поможет подобрать поверхности "
    "и реквизит, которые подходят именно этой модели, а не будут сливаться или конфликтовать.\n\n"
    "Можно фото из галереи или файлом (PNG, JPG, JPEG)."
)

NO_PHOTO_TEXT = """⚠️ Для генерации нужно фото твоих трусов.

Пришли изображение — фото из галереи или файл (PNG, JPG, JPEG).
Именно твои трусы будут основой кадра."""

WAITING_TEXT = "⏳ Генерирую изображение, жди немного...\nОбычно занимает 30–60 секунд."

ANALYZING_PANTIES_TEXT = "🔍 Смотрю на трусы — определяю материал и цвет..."

CENSORED_TEXT = (
    "🚫 Изображение не прошло через фильтры — сервис его не пропустил.\n\n"
    "Попробуй с другим фото или напиши @oreobra"
)

ERROR_TEXT = "❌ Что-то пошло не так при генерации. Попробуй ещё раз или напиши @oreobra"

RESULT_TEXT = "✅ Готово! Вот твоё изображение."

EXTRAS_QUESTION_TEXT = (
    "🎁 Хочешь добавить что-то в кадр?\n\n"
    "📇 Визитка — маленькая визитка с брендом INTIMNO\n"
    "📖 Журнал INTIMNO — журнал с названием бренда\n"
    "✏️ Описать — любой реквизит своими словами\n"
    "🖼 Прислать фото — пришли фото реквизита\n\n"
    "Или нажми «Без добавок» — и я сразу запущу генерацию."
)

FEEDBACK_QUESTION_TEXT = (
    "💬 Как вам генерация? Буду рада обратной связи — что понравилось, а что стоит поправить.\n\n"
    "Можно просто написать текстом, или выбрать вариант ниже."
)

FEEDBACK_THANKS_TEXT = "Спасибо! Учту это в следующих генерациях 🙏\n\nХочешь ещё? /reference или /describe"

# MIME types accepted as image files
_IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"}

# ──────────────────────────────────────────────────────────
#  Keyboards
# ──────────────────────────────────────────────────────────

PANTIES_READY_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[[
        InlineKeyboardButton(text="✅ Готово — продолжить", callback_data="panties_ready"),
    ]]
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

FEEDBACK_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="👍 Понравилось", callback_data="feedback_like"),
            InlineKeyboardButton(text="👎 Не то", callback_data="feedback_dislike"),
        ],
        [
            InlineKeyboardButton(text="Пропустить", callback_data="feedback_skip"),
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
    panties_file_ids: list[str],
    prompts: list[str],
) -> None:
    """
    Save generation data to state and show the extras selection menu.
    Called once prompts are ready (panties already analyzed earlier in the flow).
    """
    _extras_state = {
        "reference": ReferenceFlow.choosing_extras,
        "describe":  DescribeFlow.choosing_extras,
    }
    await state.update_data(
        flow=flow,
        panties_file_ids=panties_file_ids,
        prompts=prompts,
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
    runs all prompts in parallel, sends results as PNG files, then asks for feedback.
    """
    data = await state.get_data()
    panties_file_ids: list[str] = data["panties_file_ids"]
    base_prompts: list[str] = data["prompts"]
    total = len(base_prompts)

    gen_msg = await target.answer(WAITING_TEXT)

    # Append extras text to each prompt if provided
    prompts = (
        [f"{p}, {extras}" for p in base_prompts]
        if extras
        else base_prompts
    )

    success = 0
    try:
        panties_bytes_list = await asyncio.gather(
            *[download_telegram_file(bot, fid) for fid in panties_file_ids]
        )
        tasks = [services.generate_image(p, list(panties_bytes_list)) for p in prompts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        await gen_msg.delete()

        for idx, result in enumerate(results, start=1):
            if isinstance(result, services.CensorshipError):
                await target.answer(
                    f"🚫 Вариант {idx}/{total}: не прошло фильтры — сервис его не пропустил."
                )
            elif isinstance(result, Exception):
                logging.error("Generation %d/%d failed: %s", idx, total, result)
                await target.answer(f"❌ Вариант {idx}/{total}: ошибка генерации.")
            elif result:
                caption = RESULT_TEXT if total == 1 else f"✅ вариант {idx}/{total}"
                await send_image_as_file(target, result, caption)
                success += 1

        if success == 0:
            await target.answer(ERROR_TEXT)
        elif total > 1 and success == total:
            await target.answer(f"✅ Все {total} варианта готовы!")
        elif total > 1 and success < total:
            await target.answer(f"Готово! Получилось {success} из {total}.")

    except Exception as exc:
        logging.error("run_generation failed: %s", exc)
        try:
            await gen_msg.delete()
        except Exception:
            pass
        await target.answer(ERROR_TEXT)
    finally:
        await state.clear()

    if success > 0:
        await state.set_state(FeedbackFlow.waiting_feedback)
        await target.answer(FEEDBACK_QUESTION_TEXT, reply_markup=FEEDBACK_KEYBOARD)


# ──────────────────────────────────────────────────────────
#  Command handlers
# ──────────────────────────────────────────────────────────

async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(START_TEXT)


async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)


async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("✅ Отменено. Начни заново: /reference или /describe")


async def cmd_reference(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(ReferenceFlow.waiting_panties)
    await message.answer(PANTIES_REQUEST_TEXT)


async def cmd_describe(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(DescribeFlow.waiting_panties)
    await message.answer(PANTIES_REQUEST_TEXT)


# ──────────────────────────────────────────────────────────
#  Panties upload — shared across all flows (multi-photo, then "Готово")
# ──────────────────────────────────────────────────────────

_WAITING_PANTIES_STATES = StateFilter(
    ReferenceFlow.waiting_panties,
    DescribeFlow.waiting_panties,
)


async def got_panties_photo(message: Message, state: FSMContext) -> None:
    """Shared handler: user sends a panties photo in any waiting_panties state."""
    file_id = get_image_file_id(message)
    if not file_id:
        await message.answer(NO_PHOTO_TEXT)
        return

    data = await state.get_data()
    file_ids: list[str] = data.get("panties_file_ids", [])
    file_ids = file_ids + [file_id]
    await state.update_data(panties_file_ids=file_ids)

    count = len(file_ids)
    text = (
        "✅ Фото добавлено! Пришли ещё или нажми Готово."
        if count == 1
        else f"✅ Добавлено фото: {count}. Пришли ещё или нажми Готово."
    )
    await message.answer(text, reply_markup=PANTIES_READY_KEYBOARD)


async def panties_ready(callback: CallbackQuery, state: FSMContext) -> None:
    """Callback: user tapped «Готово» after uploading panties photo(s)."""
    data = await state.get_data()
    file_ids: list[str] = data.get("panties_file_ids", [])

    if not file_ids:
        await callback.answer("Сначала пришли хотя бы одно фото трусов 🙏", show_alert=True)
        return

    await callback.answer()
    current = await state.get_state()

    await callback.message.edit_text(
        f"✅ {'Фото' if len(file_ids) == 1 else f'{len(file_ids)} фото'} трусов получено!\n\n"
        f"{ANALYZING_PANTIES_TEXT}"
    )

    try:
        # Use the first uploaded photo as the basis for material/color analysis
        first_bytes = await download_telegram_file(callback.bot, file_ids[0])
        panties_analysis = await services.analyze_panties(first_bytes)
    except Exception as exc:
        logging.error("Panties analysis failed: %s", exc)
        await callback.message.answer(ERROR_TEXT)
        await state.clear()
        return

    await state.update_data(panties_analysis=panties_analysis)

    if current == ReferenceFlow.waiting_panties:
        await state.set_state(ReferenceFlow.waiting_reference)
        await callback.message.answer(
            "✅ Материал и цвет определены.\n\n"
            "🔍 Теперь пришли любое фото в нужном тебе стиле — с Pinterest, из интернета или свой референс.\n"
            "Можно фото из галереи или файлом (PNG, JPG, JPEG)."
        )

    elif current == DescribeFlow.waiting_panties:
        await state.set_state(DescribeFlow.waiting_description)
        await callback.message.answer(
            "✅ Материал и цвет определены.\n\n"
            "✏️ Теперь опиши желаемый стиль съёмки своими словами.\n\n"
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

    data = await state.get_data()
    panties_file_ids = data.get("panties_file_ids")
    panties_analysis = data.get("panties_analysis", "")
    if not panties_file_ids:
        await message.answer("Что-то пошло не так. Начни заново: /reference")
        await state.clear()
        return

    analyzing_msg = await message.answer("🔍 Анализирую референс, составляю промпты...")

    try:
        image_bytes = await download_telegram_file(message.bot, file_id)
        p1, p2 = await services.analyze_reference_double(image_bytes, panties_analysis)

        await analyzing_msg.delete()
        await message.answer(
            f"✅ Промпты по твоему референсу:\n\n"
            f"<b>Вариант 1:</b>\n<code>{p1}</code>\n\n"
            f"<b>Вариант 2:</b>\n<code>{p2}</code>",
            parse_mode="HTML",
        )
        await show_extras_menu(message, state, "reference", panties_file_ids, [p1, p2])

    except Exception as exc:
        logging.error("Reference analysis failed: %s", exc)
        await analyzing_msg.delete()
        await message.answer(ERROR_TEXT)
        await state.clear()


# ──────────────────────────────────────────────────────────
#  Function 2 — Describe flow
# ──────────────────────────────────────────────────────────

async def describe_got_description(message: Message, state: FSMContext) -> None:
    """State: waiting_description — user sent text style description."""
    if not message.text or not message.text.strip():
        await message.answer("Напиши описание стиля текстом, пожалуйста.")
        return

    data = await state.get_data()
    panties_file_ids = data.get("panties_file_ids")
    panties_analysis = data.get("panties_analysis", "")
    if not panties_file_ids:
        await message.answer("Что-то пошло не так. Начни заново: /describe")
        await state.clear()
        return

    analyzing_msg = await message.answer("🎨 Создаю промпт по твоему описанию...")

    try:
        prompt = await services.describe_to_prompt(message.text.strip(), panties_analysis)

        await analyzing_msg.delete()
        await message.answer(
            f"✅ Промпт по твоему описанию:\n\n<code>{prompt}</code>",
            parse_mode="HTML",
        )
        await show_extras_menu(message, state, "describe", panties_file_ids, [prompt])

    except Exception as exc:
        logging.error("Description analysis failed: %s", exc)
        await analyzing_msg.delete()
        await message.answer(ERROR_TEXT)
        await state.clear()


# ──────────────────────────────────────────────────────────
#  Extras handlers (shared across all flows)
# ──────────────────────────────────────────────────────────

_EXTRAS_TEXT_STATES = StateFilter(
    ReferenceFlow.waiting_extras_text,
    DescribeFlow.waiting_extras_text,
)

_EXTRAS_IMAGE_STATES = StateFilter(
    ReferenceFlow.waiting_extras_image,
    DescribeFlow.waiting_extras_image,
)

_CHOOSING_EXTRAS_STATES = StateFilter(
    ReferenceFlow.choosing_extras,
    DescribeFlow.choosing_extras,
)


async def extras_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    """Callback: user picked an extras option from the menu."""
    choice = callback.data
    data = await state.get_data()
    flow = data.get("flow", "reference")

    _text_state = {
        "reference": ReferenceFlow.waiting_extras_text,
        "describe":  DescribeFlow.waiting_extras_text,
    }
    _image_state = {
        "reference": ReferenceFlow.waiting_extras_image,
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
#  Feedback handlers (shared across all flows)
# ──────────────────────────────────────────────────────────

async def feedback_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Callback: user tapped a feedback button."""
    choice = callback.data

    if choice == "feedback_skip":
        await callback.message.edit_text("Хорошо! Хочешь ещё? /reference или /describe")
        await callback.answer()
        await state.clear()
        return

    if choice == "feedback_like":
        await callback.message.edit_text(
            "Рада, что понравилось! 🙌 Хочешь ещё? /reference или /describe"
        )
        await callback.answer()
        await state.clear()
        return

    if choice == "feedback_dislike":
        await callback.message.edit_text(
            "Жаль! Напиши в двух словах, что не понравилось — учту это в следующий раз "
            "(или нажми /cancel, чтобы пропустить)."
        )
        await callback.answer()
        # stay in FeedbackFlow.waiting_feedback to receive the follow-up text
        return


async def feedback_got_text(message: Message, state: FSMContext) -> None:
    """User wrote free-form feedback text after a generation."""
    text = message.text.strip() if message.text else ""
    if not text:
        await message.answer("Напиши фидбэк текстом, или /cancel чтобы пропустить.")
        return

    await state.clear()
    try:
        note = await services.summarize_feedback(text)
        if note:
            await notes.add_note(note)
    except Exception as exc:
        logging.error("Feedback summarization failed: %s", exc)

    await message.answer(FEEDBACK_THANKS_TEXT)


async def feedback_unexpected_image(message: Message, state: FSMContext) -> None:
    """Image received while waiting for feedback — just ignore feedback and clear state."""
    await state.clear()
    await message.answer("Хорошо, пропускаю фидбэк. Хочешь ещё? /reference или /describe")


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
        "Начни через /reference или /describe"
    )


async def fallback_unexpected_text(message: Message, state: FSMContext) -> None:
    """Text received outside any active flow or when image expected."""
    current = await state.get_state()
    if current in (
        ReferenceFlow.waiting_panties,
        ReferenceFlow.waiting_reference,
        DescribeFlow.waiting_panties,
    ):
        await message.answer(
            "Мне нужно изображение, не текст.\n"
            "Пришли фото из галереи или файл (PNG, JPG, JPEG)."
        )
    else:
        await message.answer(
            "Я понимаю команды и изображения.\n\n"
            "Используй /reference или /describe для начала."
        )


# ──────────────────────────────────────────────────────────
#  Commands menu (visible in Telegram UI)
# ──────────────────────────────────────────────────────────

async def set_commands(bot: Bot) -> None:
    await bot.set_my_commands([
        BotCommand(command="start",     description="Начать работу / краткая инструкция"),
        BotCommand(command="help",      description="Подробная справка"),
        BotCommand(command="reference", description="Генерация по референсу"),
        BotCommand(command="describe",  description="Описать стиль словами"),
        BotCommand(command="cancel",    description="Отменить текущее действие"),
    ])


# ──────────────────────────────────────────────────────────
#  Router registration
# ──────────────────────────────────────────────────────────

def register_handlers(dp: Dispatcher) -> None:
    # ── Commands ──────────────────────────────────────────
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_cancel, Command("cancel"))
    dp.message.register(cmd_reference, Command("reference"))
    dp.message.register(cmd_describe, Command("describe"))

    # ── Panties upload — shared across all flows (first step in every flow) ──
    dp.message.register(got_panties_photo, _WAITING_PANTIES_STATES, _IMAGE_FILTER)
    dp.message.register(got_panties_photo, _WAITING_PANTIES_STATES)
    dp.callback_query.register(panties_ready, F.data == "panties_ready", _WAITING_PANTIES_STATES)

    # ── Function 1 — Reference flow ───────────────────────
    dp.message.register(ref_got_reference, ReferenceFlow.waiting_reference, _IMAGE_FILTER)
    dp.message.register(ref_got_reference, ReferenceFlow.waiting_reference)

    # ── Function 2 — Describe flow ─────────────────────────
    dp.message.register(describe_got_description, DescribeFlow.waiting_description, F.text)
    dp.message.register(describe_unexpected_image, DescribeFlow.waiting_description, _IMAGE_FILTER)

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

    # ── Feedback (shared across all flows) ─────────────────
    dp.callback_query.register(
        feedback_callback,
        F.data.startswith("feedback_"),
        FeedbackFlow.waiting_feedback,
    )
    dp.message.register(feedback_got_text, FeedbackFlow.waiting_feedback, F.text)
    dp.message.register(feedback_unexpected_image, FeedbackFlow.waiting_feedback, _IMAGE_FILTER)

    # ── Stale "Готово" button pressed outside waiting_panties state ──
    dp.callback_query.register(
        lambda cb: cb.answer(),
        F.data == "panties_ready",
    )

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
    logging.info("Bot starting…")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
