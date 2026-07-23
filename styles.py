# ──────────────────────────────────────────────────────────
#  Style blueprints for /style
#  Claude uses these as creative direction to generate fresh prompts
#  each time — combined with the panties material/color analysis and
#  learned feedback notes, so results vary between runs.
# ──────────────────────────────────────────────────────────

STYLE_BLUEPRINTS = {
    "style_soft": {
        "name": "🌸 Нежный",
        "description": (
            "Romantic, feminine boudoir aesthetic.\n"
            "Surfaces to vary: pale milk satin, crisp white bedding, white linen, soft cream fabric, light chiffon.\n"
            "Props to vary: fresh roses, peonies, dried wildflowers, small jewelry dish, pearl necklace, "
            "delicate floral bouquet, small crystal vase, lavender sprigs.\n"
            "Lighting: soft diffused window light, gentle morning light, airy and dreamy, no harsh shadows.\n"
            "Camera angles: overhead 90° flatlay OR 70° semi-flatlay lifestyle — vary between prompts.\n"
            "Mood: romantic, Pinterest boudoir, dreamy, soft and feminine."
        ),
    },
    "style_dark": {
        "name": "🌑 Тёмный",
        "description": (
            "Moody, dark editorial aesthetic.\n"
            "Surfaces to vary: dark grey plush faux fur, silky nude fabric over a dark grey surface, "
            "matte black tray, deep charcoal velvet, dark satin.\n"
            "Props to vary: decorative candle with warm flame glow, luxury perfume bottle, "
            "black pillar candle, dark polished stone, thin dark ribbon, dried black roses.\n"
            "Lighting: dramatic softbox from 45°, warm evening lamp, moody low-key with soft dramatic shadows.\n"
            "Camera angles: overhead 90° flatlay OR 70° semi-flatlay — vary between prompts.\n"
            "Mood: moody dark editorial, high-end Instagram luxury, sensual and mysterious."
        ),
    },
    "style_rich": {
        "name": "💎 Rich",
        "description": (
            "Opulent luxury editorial aesthetic.\n"
            "Surfaces to vary: white silk kimono with subtle embroidery, cool white marble, "
            "ivory velvet fabric, champagne satin, pale gold silk.\n"
            "Props to vary: gold chain necklace, pearl earrings, pearl bracelet, "
            "luxury glass perfume bottle with gold cap, fresh white orchid blooms, "
            "INTIMNO brand fashion magazine (open, pages fanned), crystal hair pin, "
            "strand of loose pearls, gold-embossed hardcover book.\n"
            "Lighting: bright golden sunlight, warm studio lighting with gold reflectors, "
            "champagne-toned directional warm light creating rich highlights.\n"
            "Camera angles: 75°–80° semi-flatlay OR 70° lifestyle depth — vary between prompts.\n"
            "Mood: luxury boudoir, warm ivory and gold tones, high-end fashion editorial, luminous and opulent."
        ),
    },
    "style_mixed": {
        "name": "🎲 Смешанное",
        "description": (
            "Eclectic lifestyle aesthetic — surprising, unexpected prop combinations that feel fresh and fun.\n"
            "Surfaces to vary: white satin, modern grey sofa, fluffy grey faux-fur blanket on white bedding, "
            "light wooden surface, soft pastel linen.\n"
            "Props to vary: open music score book, body cream tube, bouquet of daisies, "
            "delicate gold necklace, lit candle in a black jar, white hardcover book, "
            "small potted succulent, vintage teacup and saucer, polaroid photo, dried lavender bundle.\n"
            "Lighting: bright natural daytime window light, gentle morning sunlight stripe across the surface, "
            "warm cozy evening light — vary between prompts.\n"
            "Camera angles: top-down overhead, 70° semi-flatlay, or 60° lifestyle angle — vary between prompts.\n"
            "Mood: Pinterest lifestyle, cozy and unexpected, charming Instagram aesthetic, playful yet polished."
        ),
    },
    "style_colortype": {
        "name": "🎨 Цветотип",
        "description": (
            "Color-theory-driven aesthetic — the whole composition's palette is deliberately built around "
            "the panties' own color and undertone (see the panties analysis below), like a stylist matching "
            "a full look to a color story rather than just avoiding clashes.\n"
            "Pick ONE clear color relationship per prompt and commit to it: a close analogous palette "
            "(neighboring warm or cool hues), a considered complementary contrast, or a tonal monochrome "
            "family built from the panties' own hue — vary the chosen relationship between the prompts.\n"
            "Surfaces to vary: choose surface material AND color deliberately to express the chosen palette "
            "(silk, linen, marble, velvet, paper, etc. — color-led, not fixed).\n"
            "Props to vary: jewelry, flowers, ribbons, small objects whose color intentionally continues or "
            "purposefully contrasts the chosen palette — nothing decorative that doesn't serve the color story. "
            "Also match prop TYPE to the fabric's character, not just its color: delicate/soft fabrics (cotton, "
            "jersey, simple lace) call for softer, simpler props (ribbon, small flowers, a thin delicate chain) "
            "rather than heavy opulent pieces; luxe fabrics (silk, satin, fine lace) can carry more opulent props "
            "(gold or crystal jewelry, richly textured objects).\n"
            "Lighting: choose a warm or cool color temperature that reinforces the chosen palette.\n"
            "Camera angles: vary between prompts as usual.\n"
            "Mood: intentional, editorial, color-story driven — like a fashion stylist's mood board come to life."
        ),
    },
}
