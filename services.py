import asyncio
import io
import logging

import replicate

import config
import notes

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
- Fabric/material (e.g. lace, cotton, satin, mesh, seamless microfiber, silk, ribbed jersey)
- Dominant color(s) and exact tone (e.g. warm ivory, cool jet black, dusty rose, sage green)
- Print or pattern, if any
- Overall character (delicate/romantic, sporty, bold, minimalist, luxe, playful, sheer/lingerie-lux, everyday-basic)

Then give SHORT styling guidance in 2-3 sentences: what surfaces, textures and prop colors would visually
complement this specific fabric and color WITHOUT exactly matching it or blending into it (avoid same-color-on-same-color,
avoid a busy print near an equally busy background), and what to avoid pairing it with (e.g. don't put delicate lace on a
rough raw surface, don't put a bold print near an equally busy prop).

Return ONLY this analysis, in English, no preamble, no headers, max 80 words."""


def _analyze_panties_sync(image_bytes: bytes) -> str:
    return _replicate_run(
        config.ANALYSIS_MODEL,
        {
            "system_prompt": _PANTIES_ANALYSIS_SYSTEM,
            "prompt": "Analyze the material, color and styling fit of these panties.",
            "image": io.BytesIO(image_bytes),
            "max_tokens": 1024,
            "extended_thinking": False,
        },
    )


async def analyze_panties(image_bytes: bytes) -> str:
    """Analyze a panties photo → material/color/styling guidance, used to steer prompt generation."""
    return await asyncio.to_thread(_analyze_panties_sync, image_bytes)


# ──────────────────────────────────────────────────────────
#  Reference image analysis — returns 2 prompt variants
# ──────────────────────────────────────────────────────────

def _reference_system(panties_analysis: str, notes_block: str) -> str:
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
- Starts with: "A 3:4 vertical [shot type] of women's panties from the attached image"
- The arrangement, surface/background, camera angle
- Lighting direction + type + angle
- Any props
- The mood/aesthetic
- Ends with: "ultra-realistic 4K quality, very sharp focus so the fabric from the attached panties image looks
  extremely high quality and smooth."
- Camera settings: Shot on Canon EOS R5 or Sony A7 IV, 50mm or 85mm prime lens, aperture f/4–f/8, ISO 100–200
{notes_block}

Return EXACTLY this format — nothing else:
VARIANT 1:
[first prompt]

VARIANT 2:
[second prompt]

RULES: 3:4 vertical only. Product/flatlay only — NO people. English only. Always "from the attached image".
- Show EXACTLY the same number of panties as visible in the attached image — do not add or remove any pairs
- Preserve the exact color, print, and design of the panties from the attached image — do not recolor or alter them in any way"""


def _analyze_double_sync(image_bytes: bytes, panties_analysis: str, notes_block: str) -> tuple[str, str]:
    text = _replicate_run(
        config.ANALYSIS_MODEL,
        {
            "system_prompt": _reference_system(panties_analysis, notes_block),
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


async def analyze_reference_double(image_bytes: bytes, panties_analysis: str) -> tuple[str, str]:
    """Analyze reference image + panties context → return 2 prompt variants."""
    nb = await notes.notes_block()
    return await asyncio.to_thread(_analyze_double_sync, image_bytes, panties_analysis, nb)


# ──────────────────────────────────────────────────────────
#  Text description → prompt
# ──────────────────────────────────────────────────────────

def _describe_system(panties_analysis: str, notes_block: str) -> str:
    return f"""You convert a user's style description into a professional product photography prompt for women's panties.

The user describes in Russian or English a desired shooting style.

PANTIES CONTEXT (from photo(s) the user already sent — use this to choose surfaces, colors and props that
complement the panties without exactly matching or clashing with them):
{panties_analysis}

Compose ONE prompt as a natural, vivid, specific photography brief (not a rigid fill-in-the-blank template)
that follows the user's description and is adapted to the panties context above.

The prompt MUST still include, woven in naturally:
- Starts with: "A 3:4 vertical [shot type] of women's panties from the attached image"
- The arrangement, surface/background, camera angle
- Lighting direction + type + angle
- Any props
- The mood/aesthetic
- Ends with: "ultra-realistic 4K quality, very sharp focus so the fabric from the attached panties image looks
  extremely high quality and smooth."
- Camera settings: Shot on Canon EOS R5 or Sony A7 IV, 50mm or 85mm prime lens, aperture f/4–f/8, ISO 100–200
{notes_block}

RULES: 3:4 vertical only. Product/flatlay only — NO people. English only. "from the attached image" for panties.
- Show EXACTLY the same number of panties as visible in the attached image — do not add or remove any pairs
- Preserve the exact color, print, and design of the panties from the attached image — do not recolor or alter them in any way

Return ONLY the prompt, no explanation, no preamble."""


def _describe_to_prompt_sync(description: str, panties_analysis: str, notes_block: str) -> str:
    return _replicate_run(
        config.ANALYSIS_MODEL,
        {
            "system_prompt": _describe_system(panties_analysis, notes_block),
            "prompt": description,
            "max_tokens": 1024,
            "extended_thinking": False,
        },
    )


async def describe_to_prompt(description: str, panties_analysis: str) -> str:
    """Convert the user's text style description + panties context → generation prompt."""
    nb = await notes.notes_block()
    return await asyncio.to_thread(_describe_to_prompt_sync, description, panties_analysis, nb)


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
        config.ANALYSIS_MODEL,
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
        config.ANALYSIS_MODEL,
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
