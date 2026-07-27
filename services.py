import asyncio
import io
import json
import logging

import replicate

import config
import notes
import styles

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────
#  Custom exceptions
# ──────────────────────────────────────────────────────────

class CensorshipError(Exception):
    """Raised when NanaBanana Pro blocks the image via content filters."""
    pass


# ──────────────────────────────────────────────────────────
#  Internal helpers
# ──────────────────────────────────────────────────────────

def _parse_output(output) -> str:
    """Flatten Replicate streaming output to a single string."""
    if isinstance(output, list):
        return "".join(str(t) for t in output).strip()
    return str(output).strip()


def _replicate_run(model: str, input_data: dict) -> str:
    client = replicate.Client(api_token=config.REPLICATE_API_TOKEN)
    return _parse_output(client.run(model, input=input_data))


# ──────────────────────────────────────────────────────────
#  Panties analysis — material / color / styling guidance
#  (runs first in every flow, on the first uploaded panties photo;
#   its output steers all downstream prompts)
# ──────────────────────────────────────────────────────────

_PANTIES_ANALYSIS_SYSTEM = """You are a professional lingerie product photographer's assistant.

Look at the attached photo of women's panties and identify:
- COUNT: the exact number of individual panties/pairs clearly visible in this photo (a plain integer)
- Fabric/material (e.g. lace, cotton, satin, mesh, seamless microfiber, silk, ribbed jersey)
- Dominant color(s) and exact tone (e.g. warm ivory, cool jet black, dusty rose, sage green)
- Print or pattern, if any
- Overall character (delicate/romantic, sporty, bold, minimalist, luxe, playful, sheer/lingerie-lux, everyday-basic)

Then give SHORT styling guidance in 2-3 sentences: what surfaces, textures and prop colors would visually
complement this specific fabric and color WITHOUT exactly matching it or blending into it (avoid same-color-on-same-color,
avoid a busy print near an equally busy background), and what to avoid pairing it with (e.g. don't put delicate lace on a
rough raw surface, don't put a bold print near an equally busy prop).

Return EXACTLY this format, nothing else:
COUNT: <integer>
ANALYSIS: <the fabric/color/print/character description and styling guidance, in English, max 80 words>"""


def _analyze_panties_sync(image_bytes: bytes) -> tuple[int, str]:
    text = _replicate_run(
        config.FAST_MODEL,
        {
            "system_prompt": _PANTIES_ANALYSIS_SYSTEM,
            "prompt": "Count the panties and analyze the material, color and styling fit of these panties.",
            "image": io.BytesIO(image_bytes),
            "max_tokens": 1024,
            "extended_thinking": False,
        },
    )

    count = 1
    analysis = text
    if "COUNT:" in text and "ANALYSIS:" in text:
        try:
            count_part = text.split("COUNT:", 1)[1].split("ANALYSIS:", 1)[0].strip()
            count = max(1, int("".join(ch for ch in count_part if ch.isdigit()) or "1"))
        except (ValueError, IndexError):
            count = 1
        analysis = text.split("ANALYSIS:", 1)[1].strip()

    return count, analysis


async def analyze_panties(image_bytes: bytes) -> tuple[int, str]:
    """
    Analyze a panties photo → (count of panties visible, material/color/styling guidance).
    The count is used to explicitly lock the panties count in every generated prompt.
    """
    return await asyncio.to_thread(_analyze_panties_sync, image_bytes)


def _count_phrase(count: int) -> str:
    """'the panties' for 1, 'N women's panties' for more — used inside the generated prompt text itself."""
    return "the panties" if count == 1 else f"{count} women's panties"


def _hard_rules_block(count: int) -> str:
    """
    Non-negotiable rules about count/color/material/shape preservation and prop density, injected into
    every prompt-generation system prompt. This directly targets real failure modes: the generation
    model sometimes drops/adds panties, subtly recolors/re-textures them, changes the cut/silhouette,
    adds details not present in the original, or under/over-fills the composition with props.
    """
    phrase = _count_phrase(count)
    return f"""
ABSOLUTE NON-NEGOTIABLE RULES — EVERY generated prompt MUST follow ALL of these without exception:

GARMENT COUNT:
- The attached image shows EXACTLY {count} pair(s) of panties. Every generated prompt MUST explicitly
  spell out the count, using the phrase "{phrase} from the attached image" (adapt grammar naturally,
  but the number {count} itself must appear as text in the prompt if count > 1).
- Every prompt MUST depict all {count} of them — NEVER fewer, NEVER more. Do not remove or hide any.

GARMENT IDENTITY — STRICTLY FORBIDDEN to change any of the following:
- SHAPE / CUT / SILHOUETTE: The cut of the panties (thong, string, bikini, brief, brazilian, boyshort, etc.)
  MUST remain exactly as in the attached image. NEVER change the silhouette. NEVER widen, narrow, extend
  or reshape any part of the garment.
- FABRIC / MATERIAL: The material MUST stay identical (lace stays lace, cotton stays cotton, satin stays satin,
  mesh stays mesh, etc.). NEVER substitute or blend one material with another.
- DETAILS — DO NOT ADD WHAT IS NOT THERE: If the original has no lace — do not add lace. If there is no ruffle —
  do not add ruffles. If there is no print — do not add a print. Only reproduce details that are VISIBLE in the
  attached image; do not invent, stylize, or approximate any construction detail.
- COLOR / TONE: Do NOT recolor, re-tint, or alter the panties' color, shade, or saturation in any way.
- PRINT / PATTERN: Do NOT change, simplify, redraw, or omit any print or pattern.
- FINE CONSTRUCTION: Lace trim, ruffles, edging, straps, seams must match the attached image exactly —
  preserved faithfully, never stylized or redrawn.

The panties must be reproduced as a faithful copy of the attached image — like a studio product photo of that
EXACT garment. Only the surroundings (surface, background, props, lighting) are creative territory. The garment
itself is NEVER creative territory.

WHAT IS ALLOWED (improving presentation only):
- Better lighting quality, more flattering light direction, softer shadows
- Cleaner, more premium surface / background
- Higher apparent image quality and sharpness
- Different arrangement / layout of the same garment on the surface
- Adding props / styling elements around the garment (never touching or replacing the garment itself)

LIGHTING DEFAULT: Unless the style/reference clearly calls for something else, include warm beautiful natural
white sunlight ("beautiful warm white sunlight, soft natural shadows") in each prompt.

PROP DENSITY: Unless the style direction explicitly calls for more, use only 1-2 supporting props per prompt —
keep the composition clean and uncluttered, not overcrowded.
"""


# ──────────────────────────────────────────────────────────
#  Reference image analysis — returns 2 prompt variants
# ──────────────────────────────────────────────────────────

def _reference_system(panties_analysis: str, notes_block: str, count: int) -> str:
    return f"""You are analyzing a reference image to extract shooting style parameters for two professional
product photography prompts for women's panties.

PANTIES CONTEXT (from photo(s) the user already sent — use this to choose surfaces, colors and props
that complement the panties without exactly matching or clashing with them):
{panties_analysis}

Analyze the reference image and identify shot type, camera angle, lighting (direction, type, angle),
background/surface, props, and mood/aesthetic.

Compose TWO meaningfully different prompt variants for photographing the panties in a style inspired by the
reference image, adapted to the panties' own material and color per the context above.

Write each prompt as a natural, vivid, specific photography brief — not a rigid fill-in-the-blank template.
Feel free to be creative with the arrangement, props, and mood as long as it stays true to the reference style
and the panties context. Avoid falling back on generic default setups (e.g. rose petals + white satin, or a single
candle + dark velvet) unless the reference image specifically calls for it — aim for something a little different
from previous generations each time.

Each prompt MUST still include, woven in naturally:
- Starts with: "A 3:4 vertical [shot type] of {_count_phrase(count)} from the attached image"
- The arrangement, surface/background, camera angle
- Lighting direction + type + angle
- Any props
- The mood/aesthetic
- Ends with: "ultra-realistic 4K quality, very sharp focus so the fabric from the attached panties image looks
  extremely high quality and smooth."
- Camera settings: Shot on Canon EOS R5 or Sony A7 IV, 50mm or 85mm prime lens, aperture f/4–f/8, ISO 100–200
{notes_block}
{_hard_rules_block(count)}
Return EXACTLY this format — nothing else:
VARIANT 1:
[first prompt]

VARIANT 2:
[second prompt]

RULES: 3:4 vertical only. Product/flatlay only — NO people. English only."""


def _analyze_double_sync(image_bytes: bytes, panties_analysis: str, notes_block: str, count: int) -> tuple[str, str]:
    text = _replicate_run(
        config.ANALYSIS_MODEL,
        {
            "system_prompt": _reference_system(panties_analysis, notes_block, count),
            "prompt": "Analyze this reference image and compose 2 different product photography prompt variants.",
            "image": io.BytesIO(image_bytes),
            "max_tokens": 4096,
            "extended_thinking": False,
        },
    )

    if "VARIANT 2:" in text:
        parts = text.split("VARIANT 2:", 1)
        p1 = parts[0].replace("VARIANT 1:", "").strip()
        p2 = parts[1].strip()
    elif "\n\n" in text:
        halves = text.split("\n\n", 1)
        p1 = halves[0].strip()
        p2 = halves[1].strip()
    else:
        p1 = p2 = text

    return p1, p2


async def analyze_reference_double(image_bytes: bytes, panties_analysis: str, count: int = 1) -> tuple[str, str]:
    """Analyze reference image + panties context → return 2 prompt variants."""
    nb = await notes.notes_block()
    return await asyncio.to_thread(_analyze_double_sync, image_bytes, panties_analysis, nb, count)


# ──────────────────────────────────────────────────────────
#  Text description → prompt
# ──────────────────────────────────────────────────────────

def _describe_system(panties_analysis: str, notes_block: str, count: int) -> str:
    return f"""You convert a user's style description into a professional product photography prompt for women's panties.

The user describes in Russian or English a desired shooting style.

PANTIES CONTEXT (from photo(s) the user already sent — use this to choose surfaces, colors and props that
complement the panties without exactly matching or clashing with them):
{panties_analysis}

Compose ONE prompt as a natural, vivid, specific photography brief (not a rigid fill-in-the-blank template)
that follows the user's description and is adapted to the panties context above.

The prompt MUST still include, woven in naturally:
- Starts with: "A 3:4 vertical [shot type] of {_count_phrase(count)} from the attached image"
- The arrangement, surface/background, camera angle
- Lighting direction + type + angle
- Any props
- The mood/aesthetic
- Ends with: "ultra-realistic 4K quality, very sharp focus so the fabric from the attached panties image looks
  extremely high quality and smooth."
- Camera settings: Shot on Canon EOS R5 or Sony A7 IV, 50mm or 85mm prime lens, aperture f/4–f/8, ISO 100–200
{notes_block}
{_hard_rules_block(count)}
RULES: 3:4 vertical only. Product/flatlay only — NO people. English only.

Return ONLY the prompt, no explanation, no preamble."""


def _describe_to_prompt_sync(description: str, panties_analysis: str, notes_block: str, count: int) -> str:
    return _replicate_run(
        config.ANALYSIS_MODEL,
        {
            "system_prompt": _describe_system(panties_analysis, notes_block, count),
            "prompt": description,
            "max_tokens": 1024,
            "extended_thinking": False,
        },
    )


async def describe_to_prompt(description: str, panties_analysis: str, count: int = 1) -> str:
    """Convert the user's text style description + panties context → generation prompt."""
    nb = await notes.notes_block()
    return await asyncio.to_thread(_describe_to_prompt_sync, description, panties_analysis, nb, count)


# ──────────────────────────────────────────────────────────
#  Style presets (/style) — returns 3 prompt variants
# ──────────────────────────────────────────────────────────

def _style_system(style_description: str, panties_analysis: str, notes_block: str, count: int) -> str:
    return f"""You generate product photography prompts for women's lingerie (panties).

STYLE DIRECTION (creative brief — use as inspiration, not a fill-in-the-blank checklist):
{style_description}

PANTIES CONTEXT (from photo(s) the user already sent — use this to choose surfaces, colors and props
that complement the panties without exactly matching or clashing with them):
{panties_analysis}

Compose EXACTLY 2 meaningfully different prompts within this style. Write each as a natural, vivid,
specific photography brief — not a rigid fill-in-the-blank template. The 2 must use a clearly
different surface, props and arrangement, and vary the camera angle between them. Avoid falling back on
the same generic default setups every time (e.g. always rose petals + white satin) — aim for fresh
combinations within the style each time this is run.

Each prompt MUST still include, woven in naturally:
- Starts with: "A 3:4 vertical [shot type] of {_count_phrase(count)} from the attached image"
- The arrangement, surface/background, camera angle
- Lighting direction + type + angle
- Any props
- The mood/aesthetic
- Ends with: "ultra-realistic 4K quality, very sharp focus so the fabric from the attached panties image looks
  extremely high quality and smooth."
- Camera settings: Shot on Canon EOS R5 or Sony A7 IV, 50mm or 85mm prime lens, aperture f/4–f/8, ISO 100–200
{notes_block}
{_hard_rules_block(count)}
Return EXACTLY this format — nothing else:
PROMPT 1:
[first prompt]

PROMPT 2:
[second prompt]

RULES: 3:4 vertical only. Product/flatlay only — NO people. English only.
- Stay within the style's mood and aesthetic"""


def _generate_style_prompts_sync(style_key: str, panties_analysis: str, notes_block: str, count: int) -> list[str]:
    style_description = styles.STYLE_BLUEPRINTS[style_key]["description"]
    text = _replicate_run(
        config.ANALYSIS_MODEL,
        {
            "system_prompt": _style_system(style_description, panties_analysis, notes_block, count),
            "prompt": "Generate 2 product photography prompts for this style.",
            "max_tokens": 2048,
            "extended_thinking": False,
        },
    )

    prompts = []
    for i in range(1, 3):
        marker = f"PROMPT {i}:"
        next_marker = f"PROMPT {i + 1}:" if i < 2 else None
        if marker in text:
            start = text.index(marker) + len(marker)
            end = text.index(next_marker) if next_marker and next_marker in text else len(text)
            prompts.append(text[start:end].strip())

    if len(prompts) < 2:
        parts = [p.strip() for p in text.split("\n\n") if p.strip() and not p.strip().startswith("PROMPT")]
        prompts = parts[:2] if len(parts) >= 2 else [text.strip()] * 2

    return prompts[:2]


async def generate_style_prompts(style_key: str, panties_analysis: str, count: int = 1) -> list[str]:
    """Generate 2 fresh product photography prompts for a chosen style, aware of panties material/color."""
    nb = await notes.notes_block()
    return await asyncio.to_thread(_generate_style_prompts_sync, style_key, panties_analysis, nb, count)


# ──────────────────────────────────────────────────────────
#  Color-matched accessory combo (extras: "💍 Аксессуары в тон")
# ──────────────────────────────────────────────────────────

_COLOR_ACCESSORY_SYSTEM = """Based on the fabric/color analysis of a pair of panties below, suggest a small
coordinated SET of 2-3 different prop TYPES to place together in the frame as one styled vignette — NOT a
single item. Good combinations look like: flowers + a magazine, jewelry + a small purse, a throw blanket +
berries/fruit, pearls + a book, a candle + dried flowers. Pick items that make sense placed together, not
random unrelated objects.

The set as a whole must suit BOTH:
1. Color — intentionally complements the panties WITHOUT exactly matching or clashing with them.
2. Character/type — the items' own material and style should match the fabric's character, not just color.
   Delicate/soft fabrics (cotton, jersey, simple lace) call for softer, simpler items (ribbon, small flowers,
   a delicate clip) — not heavy opulent pieces. Luxe fabrics (silk, satin, fine lace) can carry more opulent
   items (gold or crystal jewelry, richly textured objects). Sporty/everyday fabrics call for something
   casual, not jewelry-store luxury.

PANTIES ANALYSIS:
{panties_analysis}

Format: one short natural phrase listing all 2-3 items, e.g. "a small bouquet of blush roses and a glossy
magazine" or "a gold bracelet, a small beige purse and a strand of pearls". Max 20 words.
Return ONLY the phrase, nothing else."""


def _suggest_color_accessory_sync(panties_analysis: str) -> str:
    return _replicate_run(
        config.FAST_MODEL,
        {
            "system_prompt": _COLOR_ACCESSORY_SYSTEM.format(panties_analysis=panties_analysis),
            "prompt": "Suggest a coordinated set of 2-3 color-matched props.",
            "max_tokens": 1024,
            "extended_thinking": False,
        },
    )


async def suggest_color_matched_accessory(panties_analysis: str) -> str:
    """Suggest a short, color-complementary combo of 2-3 props based on the panties analysis."""
    return await asyncio.to_thread(_suggest_color_accessory_sync, panties_analysis)


# ──────────────────────────────────────────────────────────
#  Extras image analysis — short description for prompt
# ──────────────────────────────────────────────────────────

_EXTRAS_IMAGE_SYSTEM = (
    "Briefly describe this object in 5–10 words for use as a prop in a product photography prompt. "
    "Format: 'a [adjective] [object name]'. "
    "Examples: 'a small white business card', 'a glossy magazine', 'a luxury perfume bottle', "
    "'a decorative candle', 'a small bouquet of dried flowers'. "
    "Return ONLY the short description, nothing else."
)


def _analyze_extras_sync(image_bytes: bytes) -> str:
    return _replicate_run(
        config.FAST_MODEL,
        {
            "system_prompt": _EXTRAS_IMAGE_SYSTEM,
            "prompt": "Describe this object briefly.",
            "image": io.BytesIO(image_bytes),
            "max_tokens": 1024,
            "extended_thinking": False,
        },
    )


async def analyze_extras_image(image_bytes: bytes) -> str:
    """Analyze an extras prop image → short description for appending to prompt."""
    return await asyncio.to_thread(_analyze_extras_sync, image_bytes)


# ──────────────────────────────────────────────────────────
#  Feedback summarization → short note added to the learned-preferences log
# ──────────────────────────────────────────────────────────

_FEEDBACK_SUMMARY_SYSTEM = """You maintain a short internal style-notes log for an AI product-photography prompt
generator for a lingerie brand.

A user just gave feedback (in Russian or English) about a generated image.

Turn it into ONE short, generalized note in English (max 20 words) capturing the actionable preference or issue —
write it in your own words, don't translate or quote the user directly, and don't include any personal details.

If the feedback contains no specific, actionable preference or critique (e.g. it's just "thanks", "cool", "❤️",
or otherwise not useful for future generations), return exactly: NONE

Return ONLY the note text or NONE, nothing else."""


def _summarize_feedback_sync(feedback_text: str) -> str:
    return _replicate_run(
        config.FAST_MODEL,
        {
            "system_prompt": _FEEDBACK_SUMMARY_SYSTEM,
            "prompt": feedback_text,
            "max_tokens": 1024,
            "extended_thinking": False,
        },
    )


async def summarize_feedback(feedback_text: str) -> str | None:
    """Summarize raw user feedback into a short generalized note, or None if not actionable."""
    result = await asyncio.to_thread(_summarize_feedback_sync, feedback_text)
    result = result.strip()
    if not result or result.upper() == "NONE":
        return None
    return result


# ──────────────────────────────────────────────────────────
#  Dynamic, generation-specific feedback questions
# ──────────────────────────────────────────────────────────

# Used only if question generation fails — generic but still usable.
FALLBACK_FEEDBACK_QUESTIONS: list[dict] = [
    {
        "text": "Как вам в целом результат?",
        "options": [
            {"label": "👍 Нравится", "note": None},
            {"label": "😐 Так себе", "note": None},
            {"label": "👎 Не понравилось", "note": None},
        ],
    },
    {
        "text": "Поверхность/фон подошли к трусам?",
        "options": [
            {"label": "✅ Отлично подошли", "note": None},
            {"label": "😐 Нормально", "note": None},
            {
                "label": "❌ Не подошли",
                "note": "Be more careful matching the surface/background to the panties' fabric — "
                        "a recent generation's surface didn't suit it well.",
            },
        ],
    },
    {
        "text": "Реквизита/декора было...",
        "options": [
            {"label": "👌 В самый раз", "note": None},
            {"label": "🔺 Слишком много", "note": "Prefer fewer props and a more minimal amount of decor in compositions."},
            {"label": "🔻 Хотелось бы больше", "note": "Feel free to add more decorative elements/props to compositions."},
        ],
    },
    {
        "text": "Цвета в кадре сочетались хорошо?",
        "options": [
            {"label": "✅ Хорошо сочетались", "note": None},
            {
                "label": "😐 Слились в один тон",
                "note": "Ensure stronger contrast between the panties color and the surrounding palette — "
                        "avoid colors blending into one tone.",
            },
            {
                "label": "❌ Конфликтовали",
                "note": "Choose calmer, more harmonious color palettes — avoid colors that visually clash with the panties.",
            },
        ],
    },
]


def _feedback_questions_system() -> str:
    return """You are designing a short post-generation feedback survey for an AI product-photography bot
for a lingerie brand. Below is a description of what was just generated for a user.

Based on the SPECIFIC things that were actually generated (style used, composition, surface, colors, props/
extras added, number of panties shown), write 4 or 5 SPECIFIC feedback questions — NOT generic ones like
"did you like it?" or "rate 1-10". Each question should probe one particular real thing about THIS generation,
so the answers are genuinely useful for improving future prompts. Examples of the kind of specificity wanted:
if a colortype/palette style was used, ask specifically whether the color palette suited the panties; if an
accessory/prop was added, ask specifically whether that prop worked; if several panties are shown, ask
specifically whether they were all shown clearly and correctly; if a particular surface/setting was used
(e.g. wooden table, marble, fur blanket), ask specifically whether that setting worked.

Return STRICT JSON only — no markdown code fences, no commentary before or after — in exactly this shape:
{
  "questions": [
    {
      "text": "<short question in Russian, max ~12 words>",
      "options": [
        {"label": "<short button label in Russian, max ~4 words>", "note": null}
      ]
    }
  ]
}

Rules:
- Exactly 4 or 5 questions.
- Each question has 2 or 3 options.
- At least one option per question must be positive/neutral with "note": null.
- "note" must be null UNLESS the option indicates something should change for future generations — in that
  case "note" is a short, generalized, actionable instruction IN ENGLISH for a prompt-writing AI (max 15
  words), e.g. "Ensure the wooden surface tone doesn't clash with pastel-colored panties."
- Write "text" and "label" values in Russian, natural and easy to answer with one tap.
- Do not ask about anything not related to this specific generation (no generic "overall rating" question)."""


def _generate_feedback_questions_sync(context_text: str) -> list[dict]:
    text = _replicate_run(
        config.FAST_MODEL,
        {
            "system_prompt": _feedback_questions_system(),
            "prompt": context_text,
            "max_tokens": 1500,
            "extended_thinking": False,
        },
    )

    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    data = json.loads(cleaned)
    questions = data["questions"]

    validated = []
    for q in questions:
        opts = [
            {"label": str(o["label"]), "note": (str(o["note"]) if o.get("note") else None)}
            for o in q["options"]
            if o.get("label")
        ]
        if q.get("text") and 2 <= len(opts) <= 3:
            validated.append({"text": str(q["text"]), "options": opts})

    if not (4 <= len(validated) <= 5):
        raise ValueError(f"Expected 4-5 valid questions, got {len(validated)}")

    return validated


async def generate_feedback_questions(context: dict) -> list[dict]:
    """
    Generate 4-5 feedback questions tailored to what was actually generated in this run.
    Falls back to a generic fixed set if generation or parsing fails.
    """
    flow = context.get("flow", "reference")
    style_name = context.get("style_name")
    extras = context.get("extras")
    prompts = context.get("prompts", [])

    flow_description = {
        "reference": "generated using a user-provided reference photo (2 image variants were produced)",
        "describe": "generated from the user's own text description of the desired style (1 image variant)",
        "style": f"generated using the preset style '{style_name}' (2 image variants were produced)",
    }.get(flow, "generated by the bot")

    extras_line = f"Extra prop/element added to the frame: {extras}" if extras else "No extra prop was added."
    prompts_text = "\n---\n".join(prompts)[:4000]

    context_text = (
        f"Flow: {flow_description}\n"
        f"{extras_line}\n\n"
        f"Generated prompt(s) sent to the image model:\n{prompts_text}"
    )

    try:
        return await asyncio.to_thread(_generate_feedback_questions_sync, context_text)
    except Exception as exc:
        logger.error("Dynamic feedback question generation failed, using fallback: %s", exc)
        return FALLBACK_FEEDBACK_QUESTIONS


# ──────────────────────────────────────────────────────────
#  Image generation — NanaBanana Pro
# ──────────────────────────────────────────────────────────

_CENSORSHIP_KEYWORDS = [
    "nsfw", "safety", "content policy", "inappropriate",
    "explicit", "not allowed", "blocked", "violates",
]


def _generate_sync(prompt: str, panties_images_bytes: list[bytes]) -> str | None:
    """
    Call NanaBanana Pro on Replicate.
    Always 3:4 portrait, 1K resolution, PNG output.
    Accepts one or several panties photos (e.g. front/back).
    """
    client = replicate.Client(api_token=config.REPLICATE_API_TOKEN)
    output = client.run(
        config.GENERATION_MODEL,
        input={
            "prompt": prompt,
            "image_input": [io.BytesIO(b) for b in panties_images_bytes],
            "aspect_ratio": "3:4",
            "resolution": "1K",
            "output_format": "png",
            "safety_filter_level": "block_only_high",
            "allow_fallback_model": False,
        },
    )
    if isinstance(output, list):
        return str(output[0]) if output else None
    return str(output) if output else None


async def generate_image(prompt: str, panties_images_bytes: list[bytes]) -> str | None:
    """
    Generate one image via NanaBanana Pro.
    Raises CensorshipError if content filters reject the image.
    """
    try:
        return await asyncio.to_thread(_generate_sync, prompt, panties_images_bytes)
    except Exception as exc:
        error_lower = str(exc).lower()
        if any(kw in error_lower for kw in _CENSORSHIP_KEYWORDS):
            logger.warning("NanaBanana Pro: content filter blocked — %s", exc)
            raise CensorshipError() from exc
        logger.error("NanaBanana Pro: generation error — %s", exc)
        raise
