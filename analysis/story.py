"""Turns an ad image into a short first-person "product voice" story describing the
narrative the visual is telling — not just what's in the frame.

Example (given by the team) of the target output, for a collagen powder pack shot
surrounded by strawberries, bananas, and a smoothie-recipe card:

    "I am your secret to inner radiance, a premium collagen powder that's easy to
    absorb and naturally delicious. Just mix me into your favorite smoothie or
    drink, and let my goodness nourish you from within. I'm here to help you glow."
"""
from pathlib import Path

from .gemini_client import generate_from_image

STORY_PROMPT = """You are analysing a product advertisement image to reverse-engineer the \
marketing story it's telling — not to describe what's literally in the frame.

Read the image's visual composition from TOP to BOTTOM, in the order a viewer's eye would \
scan it: the top-most visual element first (hero shot, headline, or dominant subject), then \
the middle (product pack, supporting props, ingredients), then the bottom (any text, recipe \
card, CTA, or secondary detail). Use that reading order to infer what story is being told, in \
what sequence.

Then write the story as a SHORT first-person monologue spoken BY THE PRODUCT ITSELF, in the \
brand's voice — the way the product would describe its own promise to the viewer. Follow this \
shape, matching the length and tone of this example:

"I am your secret to inner radiance, a premium collagen powder that's easy to absorb and \
naturally delicious. Just mix me into your favorite smoothie or drink, and let my goodness \
nourish you from within. I'm here to help you glow."

Rules for your output:
- 2-4 sentences, first person ("I am...", "I'm here to..."), product speaking directly to the viewer.
- Name what the product IS, the core promise/benefit it's telling the viewer, how it's used \
(if the image shows this), and the emotional payoff.
- Base this only on what the image actually shows and implies — don't invent ingredients, claims, \
or a category the image doesn't support.
- Output ONLY the monologue text. No preamble, no quotation marks, no explanation.
"""


def analyze_image_story(image_path: Path) -> str:
    return generate_from_image(image_path, STORY_PROMPT)
