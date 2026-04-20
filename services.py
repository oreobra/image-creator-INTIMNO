import asyncio
import io
import logging

import replicate

import config

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
#  Reference image analysis — returns 2 prompt variants
# ──────────────────────────────────────────────────────────

_ANALYSIS_DOUBLE_SYSTEM = """You are analyzing a reference image to extract shooting style parameters for two professional product photography prompts.

Analyze the image and identify:
- Shot type (flatlay / lifestyle / catalog / editorial)
- Camera angle (overhead 90° / 70° / 60° semi-flatlay / etc.)
- Lighting: direction, type (window / softbox / golden-hour / lamp), angle
- Background / surface (fabric, color, texture)
- Props (flowers, candles, perfume, jewelry, etc.)
- Mood / aesthetic (romantic / moody / luxury / Pinterest, etc.)

Compose TWO meaningfully different prompt variants from this same reference.
Make variants differ in: arrangement, angle, or prop emphasis.

Each prompt MUST follow this exact structure:
A 3:4 vertical [shot type] of women's panties from the attached image
[arrangement] on [surface/background], [camera angle],
[lighting direction + type + angle], [props if needed],
[mood/aesthetic],
ultra-realistic 4K quality, very sharp focus so the fabric from the attached panties image looks extremely high quality and smooth.
[Camera settings: Shot on Canon EOS R5 or Sony A7 IV, 50mm or 85mm prime lens, aperture f/4–f/8, ISO 100–200]

Return EXACTLY this format — nothing else:
VARIANT 1:
[first prompt]

VARIANT 2:
[second prompt]

RULES: 3:4 vertical only. Product/flatlay only — NO people. English only. Always "from the attached image"."""


def _analyze_double_sync(image_bytes: bytes) -> tuple[str, str]:
    text = _replicate_run(
        config.ANALYSIS_MODEL,
        {
            "system_prompt": _ANALYSIS_DOUBLE_SYSTEM,
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


async def analyze_reference_double(image_bytes: bytes) -> tuple[str, str]:
    """Analyze reference image → return 2 prompt variants."""
    return await asyncio.to_thread(_analyze_double_sync, image_bytes)


# ──────────────────────────────────────────────────────────
#  Text description → prompt
# ──────────────────────────────────────────────────────────

_DESCRIBE_SYSTEM = """You convert a user's style description into a professional product photography prompt.

The user describes in Russian or English a desired shooting style for lingerie.
Compose ONE prompt following this EXACT structure:

A 3:4 vertical [shot type] of women's panties from the attached image
[arrangement] on [surface/background], [camera angle],
[lighting direction + type + angle], [props if needed],
[mood/aesthetic],
ultra-realistic 4K quality, very sharp focus so the fabric from the attached panties image looks extremely high quality and smooth.
[Camera settings: Shot on Canon EOS R5 or Sony A7 IV, 50mm or 85mm prime lens, aperture f/4–f/8, ISO 100–200]

RULES: 3:4 vertical only. Product/flatlay only — NO people. English only. "from the attached image" for panties.
Return ONLY the prompt, no explanation, no preamble."""


def _describe_to_prompt_sync(description: str) -> str:
    return _replicate_run(
        config.ANALYSIS_MODEL,
        {
            "system_prompt": _DESCRIBE_SYSTEM,
            "prompt": description,
            "max_tokens": 1024,
            "extended_thinking": False,
        },
    )


async def describe_to_prompt(description: str) -> str:
    """Convert user's text style description → generation prompt."""
    return await asyncio.to_thread(_describe_to_prompt_sync, description)


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
            "max_tokens": 60,
            "extended_thinking": False,
        },
    )


async def analyze_extras_image(image_bytes: bytes) -> str:
    """Analyze an extras prop image → short description for appending to prompt."""
    return await asyncio.to_thread(_analyze_extras_sync, image_bytes)


# ──────────────────────────────────────────────────────────
#  Image generation — NanaBanana Pro
# ──────────────────────────────────────────────────────────

_CENSORSHIP_KEYWORDS = [
    "nsfw", "safety", "content policy", "inappropriate",
    "explicit", "not allowed", "blocked", "violates",
]


def _generate_sync(prompt: str, panties_image_bytes: bytes) -> str | None:
    """
    Call NanaBanana Pro on Replicate.
    Always 3:4 portrait, 1K resolution, PNG output.
    """
    client = replicate.Client(api_token=config.REPLICATE_API_TOKEN)
    output = client.run(
        config.GENERATION_MODEL,
        input={
            "prompt": prompt,
            "image_input": [io.BytesIO(panties_image_bytes)],
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


async def generate_image(prompt: str, panties_image_bytes: bytes) -> str | None:
    """
    Generate one image via NanaBanana Pro.
    Raises CensorshipError if content filters reject the image.
    """
    try:
        return await asyncio.to_thread(_generate_sync, prompt, panties_image_bytes)
    except Exception as exc:
        error_lower = str(exc).lower()
        if any(kw in error_lower for kw in _CENSORSHIP_KEYWORDS):
            logger.warning("NanaBanana Pro: content filter blocked — %s", exc)
            raise CensorshipError() from exc
        logger.error("NanaBanana Pro: generation error — %s", exc)
        raise
