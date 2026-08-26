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

import catalog
import config
import notes
import services
import styles
from states import CatalogFlow, DescribeFlow, FeedbackFlow, ReferenceFlow, StyleFlow

# ──────────────────────────────────────────────────────────
#  Static texts
# ──────────────────────────────────────────────────────────

START_TEXT = """Привет! 👋

Я помогаю создавать профессиональные фото белья INTIMNO.

Выбери раздел:"""

MENU_GENERATE_TEXT = """🎨 <b>Генерация контента</b>

Генерирую фото белья по референсу, описанию или готовому стилю.
Выбери формат:"""

MENU_NAVIGATE_TEXT = """🗂 <b>Навигация по артикулам</b>

Все ссылки по каждому комплекту: WB, Ozon, исходники, предметка, видео.
Выбери действие:"""

HELP_TEXT = """📖 <b>Справка</b>

────────────────────
🎨 <b>ГЕНЕРАЦИЯ КОНТЕНТА</b>
────────────────────

📷 <b>/reference</b> — по референсу
1. Пришли фото трусов → нажми «Готово»
2. Пришли фото-референс в нужном стиле
Результат: 2 варианта PNG

✍️ <b>/describe</b> — описать стиль словами
1. Пришли фото трусов → нажми «Готово»
2. Опиши стиль съёмки своими словами
Результат: 1 вариант PNG

🎨 <b>/style</b> — выбрать готовый стиль
1. Пришли фото трусов → нажми «Готово»
2. Выбери один из 5 стилей: Нежный · Тёмный · Rich · Смешанное · Цветотип
Результат: 2 варианта PNG

🎡 <b>Доп. элементы</b>
После составления промпта бот предложит добавить в кадр:
Визитка · Журнал INTIMNO · Аксессуары · свой реквизит

💬 <b>Фидбэк</b>
После генерации — несколько вопросов кнопками. Помогает боту подбирать результат точнее.

────────────────────
🗂 <b>НАВИГАЦИЯ ПО АРТИКУЛАМ</b>
────────────────────

📂 <b>/catalog</b> — полный каталог
Все артикулы по категориям «Нижнее бельё» и «Быстрые запуски».
Для каждого — кнопки: WB, Ozon, исходники, предметка, на моделях, видео.

🔍 <b>/find</b> — быстрый поиск
Напиши название или часть артикула (например: <code>trysi_bikini</code>, <code>stringi</code>) — бот найдёт все совпадения.
Поиск нечёткий — название может быть неполным.
Каталог обновляется автоматически раз в неделю — данные всегда актуальны.

────────────────────
⚙️ <b>ПРОЧЕЕ</b>
────────────────────
Принимаю фото: из галереи или файлом (PNG, JPG, JPEG, WEBP)
Отдаю: PNG в полном качестве
Если что-то пошло не так → /cancel и начни заново

По вопросам: @oreobra 🙂"""

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
    "💍 Аксессуары в тон — набор из 2-3 предметов, подобранных под цвет трусов\n"
    "✏️ Описать — любой реквизит своими словами\n"
    "🖼 Прислать фото — пришли фото реквизита\n\n"
    "Или нажми «Без добавок» — и я сразу запущу генерацию."
)

FEEDBACK_CONSENT_TEXT = (
    "Не против ответить на пару быстрых вопросов? Это займёт 30 секунд и поможет мне "
    "подбирать удачнее в следующий раз 🙂"
)
FEEDBACK_GENERATING_TEXT = "Секунду, подбираю вопросы под эту генерацию..."
FEEDBACK_COMMENT_TEXT = "Хочешь добавить что-то ещё словами? Можно пропустить."
FEEDBACK_THANKS_TEXT = "Спасибо за ответы! Учту это в следующих генерациях 🙏\n\nХочешь ещё? /reference, /describe или /style"
FEEDBACK_DECLINED_TEXT = "Хорошо! Хочешь ещё? /reference, /describe или /style"
FEEDBACK_BUTTON_EXPECTED_TEXT = "Пожалуйста, выбери один из вариантов кнопкой выше 👆"

# ──────────────────────────────────────────────────────────
#  Catalog texts
# ──────────────────────────────────────────────────────────

CATALOG_MAIN_TEXT = "📂 <b>Каталог INTIMNO</b>\n\nТрусы — {total} артикулов.\nСтраница {page}/{pages}:"
CATALOG_ITEM_NOT_FOUND_TEXT = "❌ Артикул не найден. Попробуй /find или /catalog."

FIND_PROMPT_TEXT = (
    "🔍 Введи название или часть артикула для поиска.\n\n"
    "Например: <code>trysi_bikini</code>, <code>slipi</code>, <code>stringi_print</code>\n\n"
    "Поиск нечёткий — название может быть неполным."
)
FIND_NO_RESULTS_TEXT = "😕 Ничего не найдено по запросу <b>{query}</b>.\n\nПопробуй другое слово или открой /catalog."
FIND_RESULTS_TEXT = "🔍 По запросу <b>{query}</b> нашёл {count}:"

# Items per page in /catalog list
_CATALOG_PAGE_SIZE = 10

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

FEEDBACK_COMMENT_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[[
        InlineKeyboardButton(text="Пропустить", callback_data="fb_comment_skip"),
    ]]
)

# ──────────────────────────────────────────────────────────
#  Main menu keyboards
# ──────────────────────────────────────────────────────────

MAIN_MENU_KEYBOARD = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="🎨 Генерация контента", callback_data="menu:generate"),
    ],
    [
        InlineKeyboardButton(text="🗂 Навигация по артикулам", callback_data="menu:navigate"),
    ],
])

MENU_GENERATE_KEYBOARD = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📷 По референсу", callback_data="menu:go:reference")],
    [InlineKeyboardButton(text="✍️ Описать словами", callback_data="menu:go:describe")],
    [InlineKeyboardButton(text="🎨 Выбрать стиль", callback_data="menu:go:style")],
    [InlineKeyboardButton(text="← Назад", callback_data="menu:main")],
])

MENU_NAVIGATE_KEYBOARD = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📂 Каталог артикулов", callback_data="menu:go:catalog")],
    [InlineKeyboardButton(text="🔍 Найти артикул", callback_data="menu:go:find")],
    [InlineKeyboardButton(text="← Назад", callback_data="menu:main")],
])

# ──────────────────────────────────────────────────────────
#  Catalog keyboards (dynamic builders)
# ──────────────────────────────────────────────────────────

def _build_catalog_main_keyboard() -> InlineKeyboardMarkup:
    """Single button to open the full list."""
    items = catalog.get_catalog()
    total = len(items)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"🙱 Все трусы ({total})",
            callback_data="cat:list:ТРУСЫ:0",
        )],
    ])


def _build_catalog_list_keyboard(
    items: list,
    page: int,
    category: str,
) -> InlineKeyboardMarkup:
    """Paginated list of article buttons + prev/next navigation."""
    total = len(items)
    pages = max(1, -(-total // _CATALOG_PAGE_SIZE))  # ceil division
    start = page * _CATALOG_PAGE_SIZE
    page_items = items[start : start + _CATALOG_PAGE_SIZE]

    rows = [
        [InlineKeyboardButton(
            text=item["article"],
            callback_data=f"cat:item:{item['article']}",
        )]
        for item in page_items
    ]

    nav_row: list[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(
            text="← Назад",
            callback_data=f"cat:list:{category}:{page - 1}",
        ))
    if page < pages - 1:
        nav_row.append(InlineKeyboardButton(
            text=f"Далее → ({page + 2}/{pages})",
            callback_data=f"cat:list:{category}:{page + 1}",
        ))
    if nav_row:
        rows.append(nav_row)

    rows.append([InlineKeyboardButton(text="📂 К категориям", callback_data="cat:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _build_item_keyboard(item: dict) -> InlineKeyboardMarkup:
    """URL-link buttons for a single catalog item (only non-empty http links shown)."""
    rows: list[list[InlineKeyboardButton]] = []
    link_fields = [
        ("wb",          "🛒 WB"),
        ("ozon",        "🛍 Ozon"),
        ("ishodniki",   "📁 Исходники"),
        ("predmetka",   "🖼 Предметка"),
        ("na_modelyah", "👗 На моделях"),
        ("video",       "🎬 Видео"),
    ]
    for field, label in link_fields:
        value = item.get(field, "")
        if value and value.startswith("http"):
            rows.append([InlineKeyboardButton(text=label, url=value)])
    rows.append([InlineKeyboardButton(
        text="← К списку",
        callback_data=f"cat:list:{item['category']}:0",
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _item_card_text(item: dict) -> str:
    """Card text: article name + comment only. Links are shown as buttons."""
    lines = [f"📦 <b>{item['article']}</b>"]
    if item.get("comment"):
        lines.append(f"\n💬 <i>{item['comment']}</i>")
    return "\n".join(lines)




def _build_feedback_question_keyboard(question_index: int, options: list[dict]) -> InlineKeyboardMarkup:
    """One button per row — dynamic question option labels can be longer than the fixed ones were."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=opt["label"], callback_data=f"fbdyn:{question_index}:{opt_idx}")]
            for opt_idx, opt in enumerate(options)
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
    panties_analysis: str,
    style_name: str | None = None,
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
    runs all prompts in parallel, sends results as PNG files, then starts the feedback flow.
    """
    data = await state.get_data()
    panties_file_ids: list[str] = data["panties_file_ids"]
    base_prompts: list[str] = data["prompts"]
    total = len(base_prompts)

    feedback_context = {
        "flow": data.get("flow", "reference"),
        "style_name": data.get("style_name"),
        "extras": extras,
        "prompts": base_prompts,
    }

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
        await state.update_data(feedback_context=feedback_context)
        await target.answer(FEEDBACK_CONSENT_TEXT, reply_markup=FEEDBACK_CONSENT_KEYBOARD)


# ──────────────────────────────────────────────────────────
#  Command handlers
# ──────────────────────────────────────────────────────────

async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(START_TEXT, reply_markup=MAIN_MENU_KEYBOARD)


async def menu_main_callback(callback: CallbackQuery) -> None:
    """menu:main — back to main menu."""
    await callback.message.edit_text(START_TEXT, reply_markup=MAIN_MENU_KEYBOARD)
    await callback.answer()


async def menu_generate_callback(callback: CallbackQuery) -> None:
    """menu:generate — show generation section."""
    await callback.message.edit_text(
        MENU_GENERATE_TEXT, reply_markup=MENU_GENERATE_KEYBOARD, parse_mode="HTML"
    )
    await callback.answer()


async def menu_navigate_callback(callback: CallbackQuery) -> None:
    """menu:navigate — show navigation section."""
    await callback.message.edit_text(
        MENU_NAVIGATE_TEXT, reply_markup=MENU_NAVIGATE_KEYBOARD, parse_mode="HTML"
    )
    await callback.answer()


async def menu_go_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """menu:go:<action> — launch a flow from the menu button."""
    action = callback.data.split(":")[2]
    await callback.answer()

    if action == "reference":
        await state.set_state(ReferenceFlow.waiting_panties)
        await callback.message.answer(PANTIES_REQUEST_TEXT)
    elif action == "describe":
        await state.set_state(DescribeFlow.waiting_panties)
        await callback.message.answer(PANTIES_REQUEST_TEXT)
    elif action == "style":
        await state.set_state(StyleFlow.waiting_panties)
        await callback.message.answer(PANTIES_REQUEST_TEXT)
    elif action == "catalog":
        items = catalog.get_catalog()
        if not items:
            await callback.message.answer(CATALOG_EMPTY_TEXT)
        else:
            total = len(items)
            pages = max(1, -(-total // _CATALOG_PAGE_SIZE))
            text = CATALOG_MAIN_TEXT.format(category="Трусы", total=total, page=1, pages=pages)
            await callback.message.answer(
                text,
                reply_markup=_build_catalog_list_keyboard(items, 0, "ТРУСЫ"),
                parse_mode="HTML",
            )
    elif action == "find":
        await state.set_state(CatalogFlow.waiting_search)
        await callback.message.answer(FIND_PROMPT_TEXT, parse_mode="HTML")


async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, parse_mode="HTML")


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
#  /catalog — browse by category
# ──────────────────────────────────────────────────────────

async def cmd_catalog(message: Message, state: FSMContext) -> None:
    await state.clear()
    items = catalog.get_catalog()
    if not items:
        await message.answer(CATALOG_EMPTY_TEXT)
        return
    total = len(items)
    pages = max(1, -(-total // _CATALOG_PAGE_SIZE))
    text = CATALOG_MAIN_TEXT.format(category="Трусы", total=total, page=1, pages=pages)
    await message.answer(
        text,
        reply_markup=_build_catalog_list_keyboard(items, 0, "ТРУСЫ"),
        parse_mode="HTML",
    )


async def catalog_main_callback(callback: CallbackQuery) -> None:
    """cat:main — show full list from the start."""
    items = catalog.get_catalog()
    if not items:
        await callback.answer("Каталог пуст", show_alert=True)
        return
    total = len(items)
    pages = max(1, -(-total // _CATALOG_PAGE_SIZE))
    text = CATALOG_MAIN_TEXT.format(category="Трусы", total=total, page=1, pages=pages)
    await callback.message.edit_text(
        text,
        reply_markup=_build_catalog_list_keyboard(items, 0, "ТРУСЫ"),
        parse_mode="HTML",
    )
    await callback.answer()


async def catalog_list_callback(callback: CallbackQuery) -> None:
    """cat:list:ТРУСЫ:<page> — paginated article list."""
    parts = callback.data.split(":", 3)
    category = parts[2]
    page = int(parts[3]) if len(parts) > 3 else 0

    items = catalog.get_by_category(category)
    if not items:
        await callback.answer("Нет артикулов", show_alert=True)
        return

    total = len(items)
    pages = max(1, -(-total // _CATALOG_PAGE_SIZE))
    text = CATALOG_MAIN_TEXT.format(category="Трусы", total=total, page=page + 1, pages=pages)
    await callback.message.edit_text(
        text,
        reply_markup=_build_catalog_list_keyboard(items, page, category),
        parse_mode="HTML",
    )
    await callback.answer()


async def catalog_item_callback(callback: CallbackQuery) -> None:
    """cat:item:<article> — show item card with link buttons."""
    parts = callback.data.split(":", 2)
    article = parts[2] if len(parts) > 2 else ""
    item = catalog.get_by_article(article)
    if not item:
        await callback.answer(CATALOG_ITEM_NOT_FOUND_TEXT, show_alert=True)
        return
    await callback.message.edit_text(
        _item_card_text(item),
        reply_markup=_build_item_keyboard(item),
        parse_mode="HTML",
    )
    await callback.answer()


# ──────────────────────────────────────────────────────────
#  /find — fuzzy text search
# ──────────────────────────────────────────────────────────

async def cmd_find(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(CatalogFlow.waiting_search)
    await message.answer(FIND_PROMPT_TEXT, parse_mode="HTML")


async def find_got_query(message: Message, state: FSMContext) -> None:
    """User typed a search query — run fuzzy search and show results."""
    await state.clear()
    query = (message.text or "").strip()
    if not query:
        await message.answer(FIND_PROMPT_TEXT, parse_mode="HTML")
        return
    results = catalog.search_catalog(query)
    if not results:
        await message.answer(
            FIND_NO_RESULTS_TEXT.format(query=query),
            parse_mode="HTML",
        )
        return
    rows = [
        [InlineKeyboardButton(
            text=f"🙱 {r['article']}",
            callback_data=f"cat:item:{r['article']}",
        )]
        for r in results
    ]
    rows.append([InlineKeyboardButton(text="📂 Открыть каталог", callback_data="cat:main")])
    await message.answer(
        FIND_RESULTS_TEXT.format(query=query, count=len(results)),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )


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
        await show_extras_menu(callback.message, state, "style", panties_file_ids, prompts, panties_analysis, style_name)

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
        await callback.message.edit_text("💍 Подбираю реквизит в тон трусам...")
        try:
            accessories = await services.suggest_color_matched_accessory(panties_analysis)
            extras = f"with {accessories} placed in the composition"
            await callback.message.answer(f"✅ Добавляю: «{accessories}» — запускаю!")
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
    FeedbackFlow.waiting_dynamic_question,
)


async def _ask_feedback_question(message: Message, state: FSMContext) -> None:
    """Show the current question in the walk, or move on to the optional comment step if done."""
    data = await state.get_data()
    questions: list[dict] = data.get("feedback_questions", [])
    index: int = data.get("feedback_index", 0)

    if index >= len(questions):
        await message.answer(FEEDBACK_COMMENT_TEXT, reply_markup=FEEDBACK_COMMENT_KEYBOARD)
        await state.set_state(FeedbackFlow.waiting_comment)
        return

    question = questions[index]
    await message.answer(
        question["text"],
        reply_markup=_build_feedback_question_keyboard(index, question["options"]),
    )


async def feedback_consent(callback: CallbackQuery, state: FSMContext) -> None:
    """Callback: user answered whether they want to give feedback."""
    await callback.answer()

    if callback.data == "feedback_consent_no":
        await callback.message.edit_text(FEEDBACK_DECLINED_TEXT)
        await state.clear()
        return

    await callback.message.edit_text("Отлично, начнём! 🙂")
    data = await state.get_data()
    context = data.get("feedback_context", {})

    gen_msg = await callback.message.answer(FEEDBACK_GENERATING_TEXT)
    questions = await services.generate_feedback_questions(context)
    await gen_msg.delete()

    await state.update_data(feedback_questions=questions, feedback_index=0)
    await state.set_state(FeedbackFlow.waiting_dynamic_question)
    await _ask_feedback_question(callback.message, state)


async def feedback_dynamic_answer(callback: CallbackQuery, state: FSMContext) -> None:
    """Callback: user answered one of the dynamically generated questions."""
    await callback.answer()

    try:
        _, q_idx_str, opt_idx_str = callback.data.split(":")
        q_idx, opt_idx = int(q_idx_str), int(opt_idx_str)
    except (ValueError, AttributeError):
        return

    data = await state.get_data()
    questions: list[dict] = data.get("feedback_questions", [])
    if q_idx >= len(questions) or opt_idx >= len(questions[q_idx]["options"]):
        return

    option = questions[q_idx]["options"][opt_idx]
    note = option.get("note")
    if note:
        await notes.add_note(note)

    await callback.message.edit_text(f"{questions[q_idx]['text']}\n\n✅ {option['label']}")

    await state.update_data(feedback_index=q_idx + 1)
    await _ask_feedback_question(callback.message, state)


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
        BotCommand(command="start",     description="🏠 Главное меню"),
        BotCommand(command="help",      description="📖 Справка"),
        BotCommand(command="reference", description="📷 Генерация по референсу"),
        BotCommand(command="describe",  description="✍️ Генерация по описанию"),
        BotCommand(command="style",     description="🎨 Генерация по стилю"),
        BotCommand(command="catalog",   description="🗂 Каталог артикулов со всеми ссылками"),
        BotCommand(command="find",      description="🔍 Быстрый поиск по артикулу"),
        BotCommand(command="cancel",    description="❌ Отменить текущее действие"),
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
    dp.message.register(cmd_catalog, Command("catalog"))
    dp.message.register(cmd_find, Command("find"))

    # ── Main menu callbacks ──────────────────────────────
    dp.callback_query.register(menu_main_callback, F.data == "menu:main")
    dp.callback_query.register(menu_generate_callback, F.data == "menu:generate")
    dp.callback_query.register(menu_navigate_callback, F.data == "menu:navigate")
    dp.callback_query.register(menu_go_callback, F.data.startswith("menu:go:"))

    # ── Catalog navigation callbacks ───────────────────────
    dp.callback_query.register(catalog_main_callback, F.data == "cat:main")
    dp.callback_query.register(catalog_list_callback, F.data.startswith("cat:list:"))
    dp.callback_query.register(catalog_item_callback, F.data.startswith("cat:item:"))

    # ── /find search input ─────────────────────────────────
    dp.message.register(find_got_query, CatalogFlow.waiting_search, F.text)

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
    dp.callback_query.register(feedback_dynamic_answer, F.data.startswith("fbdyn:"), FeedbackFlow.waiting_dynamic_question)
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

    # Load catalog at startup (uses disk cache if available, fetches fresh otherwise)
    await catalog.load_catalog()

    # Schedule weekly auto-refresh in background
    asyncio.create_task(catalog.schedule_weekly_refresh())

    logging.info("Bot starting…")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
