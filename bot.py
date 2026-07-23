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
import styles
from states import DescribeFlow, FeedbackFlow, ReferenceFlow, StyleFlow

# ──────────────────────────────────────────────────────────
#  Static texts
# ──────────────────────────────────────────────────────────

START_TEXT = """Привет! 👋

Я генерирую профессиональные фото белья с помощью Nanobanana Pro.

📋 Доступные команды:
/reference — по референсу
/describe — описать стиль своими словами
/style — выбрать готовый стиль
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
6. Получи готовые изображения (2 варианта, PNG-файлами)

────────────────────
✏️ ФУНКЦИЯ 2 — ОПИСАТЬ СТИЛЬ (/describe)
────────────────────
1. Напиши /describe
2. Пришли фото своих трусов (одно или несколько), затем нажми «Готово»
3. Я определю материал и цвет
4. Опиши желаемый стиль съёмки словами
5. Я составлю промпт с учётом материала/цвета трусов → получи изображение (1 вариант)

────────────────────
🎨 ФУНКЦИЯ 3 — ГОТОВЫЙ СТИЛЬ (/style)
────────────────────
1. Напиши /style
2. Пришли фото своих трусов (одно или несколько), затем нажми «Готово»
3. Я определю материал и цвет
4. Выбери один из 5 стилей: 🌸 Нежный, 🌑 Тёмный, 💎 Rich, 🎲 Смешанное, 🎨 Цветотип
5. Получи 2 варианта в выбранном стиле

────────────────────
🎁 ДОП. ЭЛЕМЕНТЫ
────────────────────
После составления промпта бот предложит добавить в кадр:
📇 Визитку · 📖 Журнал INTIMNO · 💍 Аксессуары в тон (цвету трусов) · или любой реквизит своими словами / фото

────────────────────
💬 ОБРАТНАЯ СВЯЗЬ
────────────────────
После генерации бот предложит ответить на пару коротких вопросов кнопками —
это помогает подбирать удачнее в следующий раз. Можно согласиться или отказаться.

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

STYLE_MENU_TEXT = "🎨 Материал и цвет определены. Выбери стиль:"

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
    "💍 Аксессуары в тон — украшение, подобранное под цвет трусов\n"
    "✏️ Описать — любой реквизит своими словами\n"
    "🖼 Прислать фото — пришли фото реквизита\n\n"
    "Или нажми «Без добавок» — и я сразу запущу генерацию."
)

FEEDBACK_CONSENT_TEXT = (
    "Не против ответить на пару быстрых вопросов? Это займёт 30 секунд и поможет мне "
    "подбирать удачнее в следующий раз 🙂"
)
FEEDBACK_Q1_TEXT = "1/4 — Как вам в целом результат?"
FEEDBACK_Q2_TEXT = "2/4 — Поверхность/фон подошли к трусам?"
FEEDBACK_Q3_TEXT = "3/4 — Реквизита/декора было..."
FEEDBACK_Q4_TEXT = "4/4 — Цвета в кадре сочетались хорошо?"
FEEDBACK_COMMENT_TEXT = "Хочешь добавить что-то ещё словами? Можно пропустить."
FEEDBACK_THANKS_TEXT = "Спасибо за ответы! Учту это в следующих генерациях 🙏\n\nХочешь ещё? /reference, /describe или /style"
FEEDBACK_DECLINED_TEXT = "Хорошо! Хочешь ещё? /reference, /describe или /style"
FEEDBACK_BUTTON_EXPECTED_TEXT = "Пожалуйста, выбери один из вариантов кнопкой выше 👆"

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


def _build_style_keyboard() -> InlineKeyboardMarkup:
    keys = list(styles.STYLE_BLUEPRINTS.keys())
    rows = []
    for i in range(0, len(keys), 2):
        pair = keys[i:i + 2]
        rows.append([
            InlineKeyboardButton(text=styles.STYLE_BLUEPRINTS[k]["name"], callback_data=k)
            for k in pair
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


STYLE_KEYBOARD = _build_style_keyboard()

EXTRAS_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="📇 Визитка", callback_data="extras_card"),
            InlineKeyboardButton(text="📖 Журнал INTIMNO", callback_data="extras_magazine"),
        ],
        [
            InlineKeyboardButton(text="💍 Аксессуары в тон", callback_data="extras_accessories"),
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

FEEDBACK_CONSENT_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[[
        InlineKeyboardButton(text="Да, давай", callback_data="feedback_consent_yes"),
        InlineKeyboardButton(text="В другой раз", callback_data="feedback_consent_no"),
    ]]
)

FEEDBACK_Q1_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[[
        InlineKeyboardButton(text="👍 Нравится", callback_data="fb_q1_like"),
        InlineKeyboardButton(text="😐 Так себе", callback_data="fb_q1_meh"),
        InlineKeyboardButton(text="👎 Не понравилось", callback_data="fb_q1_dislike"),
    ]]
)

FEEDBACK_Q2_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[[
        InlineKeyboardButton(text="✅ Отлично подошли", callback_data="fb_q2_good"),
        InlineKeyboardButton(text="😐 Нормально", callback_data="fb_q2_ok"),
        InlineKeyboardButton(text="❌ Не подошли", callback_data="fb_q2_bad"),
    ]]
)

FEEDBACK_Q3_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[[
        InlineKeyboardButton(text="👌 В самый раз", callback_data="fb_q3_right"),
        InlineKeyboardButton(text="🔺 Слишком много", callback_data="fb_q3_much"),
        InlineKeyboardButton(text="🔻 Хотелось бы больше", callback_data="fb_q3_less"),
    ]]
)

FEEDBACK_Q4_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[[
        InlineKeyboardButton(text="✅ Хорошо сочетались", callback_data="fb_q4_good"),
        InlineKeyboardButton(text="😐 Слились в один тон", callback_data="fb_q4_blend"),
        InlineKeyboardButton(text="❌ Конфликтовали", callback_data="fb_q4_clash"),
    ]]
)

FEEDBACK_COMMENT_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[[
        InlineKeyboardButton(text="Пропустить", callback_data="fb_comment_skip"),
    ]]
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
    panties_analysis: str,
) -> None:
    """
    Save generation data to state and show the extras selection menu.
    Called once prompts are ready (panties already analyzed earlier in the flow).
    """
    _extras_state = {
        "reference": ReferenceFlow.choosing_extras,
        "describe":  DescribeFlow.choosing_extras,
        "style":     StyleFlow.choosing_extras,
    }
    await state.update_data(
        flow=flow,
        panties_file_ids=panties_file_ids,
        prompts=prompts,
        panties_analysis=panties_analysis,
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
    runs all prompts in parallel, sends results as PNG files, then starts the feedback flow.
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
        await state.set_state(FeedbackFlow.waiting_consent)
        await target.answer(FEEDBACK_CONSENT_TEXT, reply_markup=FEEDBACK_CONSENT_KEYBOARD)


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
    await message.answer("✅ Отменено. Начни заново: /reference, /describe или /style")


async def cmd_reference(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(ReferenceFlow.waiting_panties)
    await message.answer(PANTIES_REQUEST_TEXT)


async def cmd_describe(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(DescribeFlow.waiting_panties)
    await message.answer(PANTIES_REQUEST_TEXT)


async def cmd_style(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(StyleFlow.waiting_panties)
    await message.answer(PANTIES_REQUEST_TEXT)


# ──────────────────────────────────────────────────────────
#  Panties upload — shared across all flows (multi-photo, then "Готово")
# ──────────────────────────────────────────────────────────

_WAITING_PANTIES_STATES = StateFilter(
    ReferenceFlow.waiting_panties,
    DescribeFlow.waiting_panties,
    StyleFlow.waiting_panties,
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
        panties_count, panties_analysis = await services.analyze_panties(first_bytes)
    except Exception as exc:
        logging.error("Panties analysis failed: %s", exc)
        await callback.message.answer(ERROR_TEXT)
        await state.clear()
        return

    await state.update_data(panties_analysis=panties_analysis, panties_count=panties_count)

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

    elif current == StyleFlow.waiting_panties:
        await state.set_state(StyleFlow.choosing_style)
        await callback.message.answer(STYLE_MENU_TEXT, reply_markup=STYLE_KEYBOARD)


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
    panties_count = data.get("panties_count", 1)
    if not panties_file_ids:
        await message.answer("Что-то пошло не так. Начни заново: /reference")
        await state.clear()
        return

    analyzing_msg = await message.answer("🔍 Анализирую референс, составляю промпты...")

    try:
        image_bytes = await download_telegram_file(message.bot, file_id)
        p1, p2 = await services.analyze_reference_double(image_bytes, panties_analysis, panties_count)

        await analyzing_msg.delete()
        await message.answer(
            f"✅ Промпты по твоему референсу:\n\n"
            f"<b>Вариант 1:</b>\n<code>{p1}</code>\n\n"
            f"<b>Вариант 2:</b>\n<code>{p2}</code>",
            parse_mode="HTML",
        )
        await show_extras_menu(message, state, "reference", panties_file_ids, [p1, p2], panties_analysis)

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
    panties_count = data.get("panties_count", 1)
    if not panties_file_ids:
        await message.answer("Что-то пошло не так. Начни заново: /describe")
        await state.clear()
        return

    analyzing_msg = await message.answer("🎨 Создаю промпт по твоему описанию...")

    try:
        prompt = await services.describe_to_prompt(message.text.strip(), panties_analysis, panties_count)

        await analyzing_msg.delete()
        await message.answer(
            f"✅ Промпт по твоему описанию:\n\n<code>{prompt}</code>",
            parse_mode="HTML",
        )
        await show_extras_menu(message, state, "describe", panties_file_ids, [prompt], panties_analysis)

    except Exception as exc:
        logging.error("Description analysis failed: %s", exc)
        await analyzing_msg.delete()
        await message.answer(ERROR_TEXT)
        await state.clear()


# ──────────────────────────────────────────────────────────
#  Function 3 — Style flow
# ──────────────────────────────────────────────────────────

async def style_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    """Callback: user picked one of the 5 preset styles."""
    style_key = callback.data
    if style_key not in styles.STYLE_BLUEPRINTS:
        await callback.answer()
        return

    style_name = styles.STYLE_BLUEPRINTS[style_key]["name"]
    data = await state.get_data()
    panties_file_ids = data.get("panties_file_ids")
    panties_analysis = data.get("panties_analysis", "")
    panties_count = data.get("panties_count", 1)
    if not panties_file_ids:
        await callback.answer()
        await callback.message.answer("Что-то пошло не так. Начни заново: /style")
        await state.clear()
        return

    await callback.answer()
    await callback.message.edit_text(f"🎨 Стиль «{style_name}» — генерирую 2 промпта...")

    try:
        prompts = await services.generate_style_prompts(style_key, panties_analysis, panties_count)

        numbered = "\n\n".join(f"<b>Вариант {i}:</b>\n<code>{p}</code>" for i, p in enumerate(prompts, start=1))
        await callback.message.answer(
            f"✅ Промпты в стиле «{style_name}»:\n\n{numbered}",
            parse_mode="HTML",
        )
        await show_extras_menu(callback.message, state, "style", panties_file_ids, prompts, panties_analysis)

    except Exception as exc:
        logging.error("Style prompt generation failed: %s", exc)
        await callback.message.answer(ERROR_TEXT)
        await state.clear()


# ──────────────────────────────────────────────────────────
#  Extras handlers (shared across all flows)
# ──────────────────────────────────────────────────────────

_EXTRAS_TEXT_STATES = StateFilter(
    ReferenceFlow.waiting_extras_text,
    DescribeFlow.waiting_extras_text,
    StyleFlow.waiting_extras_text,
)

_EXTRAS_IMAGE_STATES = StateFilter(
    ReferenceFlow.waiting_extras_image,
    DescribeFlow.waiting_extras_image,
    StyleFlow.waiting_extras_image,
)

_CHOOSING_EXTRAS_STATES = StateFilter(
    ReferenceFlow.choosing_extras,
    DescribeFlow.choosing_extras,
    StyleFlow.choosing_extras,
)


async def extras_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    """Callback: user picked an extras option from the menu."""
    choice = callback.data
    data = await state.get_data()
    flow = data.get("flow", "reference")
    panties_analysis = data.get("panties_analysis", "")

    _text_state = {
        "reference": ReferenceFlow.waiting_extras_text,
        "describe":  DescribeFlow.waiting_extras_text,
        "style":     StyleFlow.waiting_extras_text,
    }
    _image_state = {
        "reference": ReferenceFlow.waiting_extras_image,
        "describe":  DescribeFlow.waiting_extras_image,
        "style":     StyleFlow.waiting_extras_image,
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

    elif choice == "extras_accessories":
        await callback.answer()
        await callback.message.edit_text("💍 Подбираю аксессуар в тон трусам...")
        try:
            accessory = await services.suggest_color_matched_accessory(panties_analysis)
            extras = f"with {accessory} placed in the composition"
            await callback.message.answer(f"✅ Добавляю: «{accessory}» — запускаю!")
            await run_generation(callback.message, callback.bot, state, extras)
        except Exception as exc:
            logging.error("Color-matched accessory suggestion failed: %s", exc)
            await callback.message.answer(ERROR_TEXT)
            await state.clear()

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
#  Feedback handlers — guided Q&A (shared across all flows)
# ──────────────────────────────────────────────────────────

_FEEDBACK_BUTTON_STATES = StateFilter(
    FeedbackFlow.waiting_consent,
    FeedbackFlow.waiting_q1,
    FeedbackFlow.waiting_q2,
    FeedbackFlow.waiting_q3,
    FeedbackFlow.waiting_q4,
)


async def feedback_consent(callback: CallbackQuery, state: FSMContext) -> None:
    """Callback: user answered whether they want to give feedback."""
    await callback.answer()

    if callback.data == "feedback_consent_no":
        await callback.message.edit_text(FEEDBACK_DECLINED_TEXT)
        await state.clear()
        return

    await callback.message.edit_text("Отлично, начнём! 🙂")
    await callback.message.answer(FEEDBACK_Q1_TEXT, reply_markup=FEEDBACK_Q1_KEYBOARD)
    await state.set_state(FeedbackFlow.waiting_q1)


async def feedback_q1(callback: CallbackQuery, state: FSMContext) -> None:
    """Callback: overall impression — informational only, no note stored."""
    await callback.answer()
    await callback.message.edit_text("Записала ✍️")
    await callback.message.answer(FEEDBACK_Q2_TEXT, reply_markup=FEEDBACK_Q2_KEYBOARD)
    await state.set_state(FeedbackFlow.waiting_q2)


async def feedback_q2(callback: CallbackQuery, state: FSMContext) -> None:
    """Callback: did the surface/background suit the panties."""
    await callback.answer()
    if callback.data == "fb_q2_bad":
        await notes.add_note(
            "Be more careful matching the surface/background to the panties' fabric — "
            "a recent generation's surface didn't suit it well."
        )
    await callback.message.edit_text("Записала ✍️")
    await callback.message.answer(FEEDBACK_Q3_TEXT, reply_markup=FEEDBACK_Q3_KEYBOARD)
    await state.set_state(FeedbackFlow.waiting_q3)


async def feedback_q3(callback: CallbackQuery, state: FSMContext) -> None:
    """Callback: amount of props/decor."""
    await callback.answer()
    if callback.data == "fb_q3_much":
        await notes.add_note("Prefer fewer props and a more minimal amount of decor in compositions.")
    elif callback.data == "fb_q3_less":
        await notes.add_note("Feel free to add more decorative elements/props to compositions.")
    await callback.message.edit_text("Записала ✍️")
    await callback.message.answer(FEEDBACK_Q4_TEXT, reply_markup=FEEDBACK_Q4_KEYBOARD)
    await state.set_state(FeedbackFlow.waiting_q4)


async def feedback_q4(callback: CallbackQuery, state: FSMContext) -> None:
    """Callback: did the colors work together."""
    await callback.answer()
    if callback.data == "fb_q4_blend":
        await notes.add_note(
            "Ensure stronger contrast between the panties color and the surrounding palette — "
            "avoid colors blending into one tone."
        )
    elif callback.data == "fb_q4_clash":
        await notes.add_note(
            "Choose calmer, more harmonious color palettes — avoid colors that visually clash with the panties."
        )
    await callback.message.edit_text("Записала ✍️")
    await callback.message.answer(FEEDBACK_COMMENT_TEXT, reply_markup=FEEDBACK_COMMENT_KEYBOARD)
    await state.set_state(FeedbackFlow.waiting_comment)


async def feedback_comment_skip(callback: CallbackQuery, state: FSMContext) -> None:
    """Callback: user skipped the optional free-text comment."""
    await callback.answer()
    await callback.message.edit_text(FEEDBACK_THANKS_TEXT)
    await state.clear()


async def feedback_comment_text(message: Message, state: FSMContext) -> None:
    """User wrote a free-form comment to close out the feedback Q&A."""
    text = message.text.strip() if message.text else ""
    if not text:
        await message.answer("Напиши комментарий текстом, или нажми «Пропустить».")
        return

    await state.clear()
    try:
        note = await services.summarize_feedback(text)
        if note:
            await notes.add_note(note)
    except Exception as exc:
        logging.error("Feedback summarization failed: %s", exc)

    await message.answer(FEEDBACK_THANKS_TEXT)


async def feedback_comment_unexpected_image(message: Message, state: FSMContext) -> None:
    """Image received while waiting for the optional comment — just wrap up."""
    await state.clear()
    await message.answer(FEEDBACK_THANKS_TEXT)


async def feedback_button_expected(message: Message) -> None:
    """Text/image received while a feedback question expects a button tap."""
    await message.answer(FEEDBACK_BUTTON_EXPECTED_TEXT)


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
        "Начни через /reference, /describe или /style"
    )


async def fallback_unexpected_text(message: Message, state: FSMContext) -> None:
    """Text received outside any active flow or when image expected."""
    current = await state.get_state()
    if current in (
        ReferenceFlow.waiting_panties,
        ReferenceFlow.waiting_reference,
        DescribeFlow.waiting_panties,
        StyleFlow.waiting_panties,
    ):
        await message.answer(
            "Мне нужно изображение, не текст.\n"
            "Пришли фото из галереи или файл (PNG, JPG, JPEG)."
        )
    else:
        await message.answer(
            "Я понимаю команды и изображения.\n\n"
            "Используй /reference, /describe или /style для начала."
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
        BotCommand(command="style",     description="Выбрать готовый стиль"),
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
    dp.message.register(cmd_style, Command("style"))

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

    # ── Function 3 — Style flow ────────────────────────────
    dp.callback_query.register(
        style_chosen,
        F.data.in_(styles.STYLE_BLUEPRINTS.keys()),
        StyleFlow.choosing_style,
    )

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

    # ── Feedback — guided Q&A (shared across all flows) ────
    dp.callback_query.register(feedback_consent, F.data.startswith("feedback_consent_"), FeedbackFlow.waiting_consent)
    dp.callback_query.register(feedback_q1, F.data.startswith("fb_q1_"), FeedbackFlow.waiting_q1)
    dp.callback_query.register(feedback_q2, F.data.startswith("fb_q2_"), FeedbackFlow.waiting_q2)
    dp.callback_query.register(feedback_q3, F.data.startswith("fb_q3_"), FeedbackFlow.waiting_q3)
    dp.callback_query.register(feedback_q4, F.data.startswith("fb_q4_"), FeedbackFlow.waiting_q4)
    dp.callback_query.register(feedback_comment_skip, F.data == "fb_comment_skip", FeedbackFlow.waiting_comment)
    dp.message.register(feedback_comment_text, FeedbackFlow.waiting_comment, F.text)
    dp.message.register(feedback_comment_unexpected_image, FeedbackFlow.waiting_comment, _IMAGE_FILTER)
    dp.message.register(feedback_button_expected, _FEEDBACK_BUTTON_STATES)

    # ── Stale buttons pressed outside their expected state ─
    dp.callback_query.register(lambda cb: cb.answer(), F.data == "panties_ready")
    dp.callback_query.register(lambda cb: cb.answer(), F.data.in_(styles.STYLE_BLUEPRINTS.keys()))

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
