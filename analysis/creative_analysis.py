"""Deeper creative-strategy read on one competitor ad: what marketing pattern
("creative root") it's using, why it works, and whether/how that pattern could
be adapted for Dr. Bimal's Arjuna Cardio Care Tea within our compliance rules.

This is grounded with compliance.rules.compliance_brief() so Gemini's "could this
work for us" reasoning doesn't suggest anything the ruleset already bans — but
its output is still a creative-strategy opinion, not a compliance sign-off. Run
the result through compliance.validate before using any suggested copy verbatim.
"""
import json
from pathlib import Path

from compliance.rules import compliance_brief, load_rules

from .gemini_client import generate_json_from_image

PROMPT_TEMPLATE = """You are a creative strategist reverse-engineering competitor ad creatives to find \
reusable marketing patterns for our own product.

Read the ad image's composition from TOP to BOTTOM, the order a viewer's eye scans it, and read it \
together with the ad's actual copy below.

COMPETITOR AD COPY:
Page: {page_name}
Headline/title: {title}
Body text: {body_text}
CTA: {cta_text}

{compliance_brief}

Analyze this ad and return ONLY a JSON object with exactly these keys:

- "creative_root": a short (3-6 word) name for the underlying marketing pattern/archetype this ad is \
built on, in "Category: Specific angle" form, e.g. "Problem-Solution: Lifestyle Risk", \
"Social Proof: Before/After", "Authority: Ingredient Science". Base this on the actual structure of \
the ad (what problem it opens with, how it resolves it, what it leans on for credibility), not a \
generic label.

- "mechanism": ONE sentence explaining the psychological mechanism that makes this root work on a \
viewer — why this structure persuades, not what it literally shows.

- "visual_motif": ONE sentence describing the visual composition strategy (how the image is staged \
to support the mechanism above) — reference actual elements visible in the image.

- "applicability": 2-4 sentences assessing whether and how this creative root could work for OUR \
product (named above), reasoning explicitly against the compliance constraints listed above. If the \
competitor's ad uses anything our constraints forbid (a disease claim, a timeline, an endorsement- \
style doctor mention, an unapproved ingredient claim), name that specifically and say what we'd have \
to change to reuse the underlying pattern compliantly. If the root doesn't translate to our product \
at all, say so plainly instead of forcing a fit.

- "story": a short (2-4 sentence) first-person monologue spoken BY OUR PRODUCT (not the competitor's), \
in a warm, direct voice — it may open by naming the viewer's situation before introducing itself, \
in this shape: "Hey, I see you're [situation] — I'm here to help. I'm [product], your [role], \
[what it does]." Base this on the creative root you identified, adapted to be compliant with the \
constraints above — do not include any banned verb, disease term, timeline, or endorsement language.

- "storyboard": an array of 3 objects, each {{"section": "Top"|"Middle"|"Bottom", "description": ...}}, \
breaking the ad's visual composition into what occupies the top, middle, and bottom of the frame, in \
that reading order.

Output ONLY the JSON object, no markdown fences, no preamble.
"""


def analyze_ad_creative(ad: dict, image_path: Path) -> dict:
    rules = load_rules()
    prompt = PROMPT_TEMPLATE.format(
        page_name=ad.get("page_name") or "Unknown",
        title=ad.get("title") or "(none)",
        body_text=ad.get("body_text") or "(none)",
        cta_text=ad.get("cta_text") or "(none)",
        compliance_brief=compliance_brief(rules),
    )
    raw = generate_json_from_image(image_path, prompt)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Gemini did not return valid JSON: {raw[:300]}") from e

    required = {"creative_root", "mechanism", "visual_motif", "applicability", "story", "storyboard"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"Gemini response missing keys {missing}: {raw[:300]}")
    return data
