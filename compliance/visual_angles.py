"""Enumerates feasible ad visual angles for Dr. Bimal's Arjuna Cardio Care Tea and
generates an image-generation prompt for each.

The taxonomy itself is deterministic and derived directly from rules.yaml's
headline_types (A/B/C safe, D banned) crossed with the Annexure A "Modern medicine
(IMC)" feasibility table in legal_opinion_summary.md — it is NOT invented by an LLM,
because getting this wrong has real legal exposure. Use this module to decide *which*
angles are worth generating; use analysis/story.py or an image model to actually
render them.
"""
from dataclasses import dataclass, field

from .rules import load_rules

RiskLevel = str  # "Safe" | "Conditional" | "Avoid"


@dataclass
class VisualAngle:
    id: str
    name: str
    headline_type: str  # A / B / C / D
    doctor_usage: str
    risk: RiskLevel
    description: str
    checklist: list[str]
    example_headline: str
    negative_constraints: list[str] = field(default_factory=list)

    def prompt(self, rules: dict) -> str:
        product = rules["product"]
        disclaimer = rules["disclaimer"]["text_en"]
        base_negatives = [
            "no medical attire (no lab coat, no stethoscope, no clinical insignia)",
            "no disease imagery (no heart-attack, hospital, or diagnostic imagery)",
            "no fabricated certification badges, seals, or credential grids",
            "no before/after medical imagery",
            "no fake star ratings or testimonial overlays",
        ]
        negatives = base_negatives + self.negative_constraints

        lines = [
            f"Product ad visual for {product['name']} ({product['brand']}, {product['pack']}, "
            f"₹{product['price_inr']} / ₹{product['per_day_inr']} per day). {product['type']}, "
            f"made of {product['ingredient_count']}: {', '.join(product['key_herbs'])}.",
            "",
            f"Angle: {self.name} — {self.description}",
            "",
            "Compose the frame top to bottom, in this order:",
            f"1. Top third — visual hook: {self._top_third()}",
            f"2. Middle third — hero subject: {self._middle_third(product)}",
            f"3. Bottom third — text overlay: headline \"{self.example_headline}\"",
        ]
        if self.doctor_usage != "none":
            lines.append(f"   Doctor attribution line: \"Formulated by {product['formulator']}\", "
                          f"small text, separate from the headline, {self.doctor_usage}.")
        lines.append(f"   Disclaimer (small print, bottom edge, high-contrast): \"{disclaimer}\"")
        lines.append("")
        lines.append("Style: warm, natural-light Ayurvedic wellness photography; earthy palette "
                      "(terracotta, sage green, cream); no harsh clinical whites or blues.")
        lines.append("")
        lines.append("Do NOT include: " + "; ".join(negatives) + ".")
        return "\n".join(lines)

    def _top_third(self) -> str:
        return {
            "A": "soft morning light, a calm domestic setting (kitchen counter or bedside table)",
            "B": "a relatable everyday moment that hints at the consumer's unspoken worry, no text yet",
            "C": "a macro/close-up of the named herb in its raw form (bark, leaf, root)",
        }.get(self.headline_type, "neutral lifestyle backdrop")

    def _middle_third(self, product: dict) -> str:
        return (f"the {product['brand']} tea pack and a steaming cup of brewed tea, "
                f"packaging clearly legible")


def _angles() -> list[VisualAngle]:
    return [
        VisualAngle(
            id="broad_wellness_ritual",
            name="Broad wellness ritual",
            headline_type="A",
            doctor_usage="none",
            risk="Safe",
            description="A calm daily-ritual lifestyle shot; no disease term, no doctor, no claim "
                         "specific enough to test or disprove.",
            checklist=[
                "Headline is Type A (broad wellness) — e.g. \"A daily ritual for a healthy heart.\"",
                "No disease term anywhere in headline or body copy.",
                "No doctor name/photo required.",
            ],
            example_headline="A daily ritual for a healthy heart.",
        ),
        VisualAngle(
            id="consumer_fear_hook",
            name="Consumer-fear question hook",
            headline_type="B",
            doctor_usage="none",
            risk="Safe",
            description="Names the consumer's own worry as a question, not a product claim — "
                         "pattern-interrupts without asserting anything about the product.",
            checklist=[
                "Headline is phrased as a question about the consumer, not a statement about the product.",
                "No disease term in the question itself (frame around a habit/worry, not a diagnosis).",
                "Disclaimer still recommended since the ad is clearly cardio-context.",
            ],
            example_headline="Tried every home remedy for your heart?",
        ),
        VisualAngle(
            id="ingredient_hero",
            name="Ingredient hero shot",
            headline_type="C",
            doctor_usage="none",
            risk="Safe",
            description="Macro shot of a named herb (default: Arjuna Chhal) with an approved, "
                         "ingredient-attributed claim as the headline — the ingredient is the subject, "
                         "never the product or the doctor.",
            checklist=[
                "Headline is an approved claim string from rules.yaml verbatim, e.g. "
                "\"Arjuna Chhal helps reduce bad cholesterol.\"",
                "Small-print research citation included (e.g. \"Gupta et al. 2001, JAPI\").",
                "Do not substitute a different verb or extend the claim beyond the approved wording.",
            ],
            example_headline="Arjuna Chhal helps reduce bad cholesterol.",
        ),
        VisualAngle(
            id="doctor_formulation_card",
            name="Doctor formulation credibility card",
            headline_type="A",
            doctor_usage="name and title only, no photograph",
            risk="Safe",
            description="Recommended default way to use the doctor at all: name + credentials as a "
                         "factual attribution line, kept visually separate from any efficacy headline, "
                         "per Annexure B Do #1.",
            checklist=[
                "No photo of the doctor.",
                "Attribution text matches an allowed_pattern from rules.yaml exactly, e.g. "
                "\"Formulated by Dr. Bimal Chhajer MBBS MD.\"",
                "No verb from doctor.banned_near_name on the same line as the name.",
                "Attribution line is visually separated from the product-benefit headline.",
            ],
            example_headline="A daily ritual for a healthy heart.",
        ),
        VisualAngle(
            id="doctor_portrait_attribution",
            name="Doctor portrait + authorship attribution",
            headline_type="A",
            doctor_usage="photograph (non-medical attire), paired with an authorship attribution",
            risk="Conditional",
            description="Annexure A treats this as legally defensible, but flags a high likelihood "
                         "of a state medical council taking a contrary view that then has to be "
                         "litigated. Use sparingly and get explicit legal sign-off before running it "
                         "at scale.",
            checklist=[
                "Doctor is NOT wearing medical attire (no lab coat, no stethoscope).",
                "Photo is paired with an authorship attribution, not a recommendation.",
                "Product remains the visual focus, not the doctor's credentials.",
                "Flag for case-by-case legal review before scaled spend, per the opinion's own caveat.",
            ],
            example_headline="A daily ritual for a healthy heart.",
        ),
        VisualAngle(
            id="trademarked_avatar",
            name="Trademarked animated avatar",
            headline_type="A",
            doctor_usage="registered-trademark animated avatar (stylised, not photorealistic)",
            risk="Safe",
            description="Lower long-term risk substitute for a real photo — proprietary trademark "
                         "rights survive even if a medical council restricts use of the RMP's actual "
                         "likeness. Keep the avatar stylised/abstracted rather than an exact "
                         "resemblance, which the opinion treats as safer.",
            checklist=[
                "Avatar is stylised/abstracted, not a photorealistic likeness.",
                "Avatar is the team's registered trademark (confirm registration before use).",
                "Pair with authorship attribution text, not a recommendation.",
            ],
            example_headline="A daily ritual for a healthy heart.",
        ),
        VisualAngle(
            id="value_price_callout",
            name="Value / price callout",
            headline_type="A",
            doctor_usage="none",
            risk="Safe",
            description="Price-led creative — combine with the broad-wellness or ingredient angle, "
                         "never as a standalone justification for a health claim.",
            checklist=[
                "MRP shown must be the real declared packaging MRP — no fabricated strikethrough anchor.",
                "Price framed as value (₹12/day), not as a cure-for-cost tradeoff.",
            ],
            example_headline="₹12 a day for a heart-healthy ritual.",
        ),
        VisualAngle(
            id="banned_disease_cure_angle",
            name="[REFERENCE ONLY — do not generate] Disease/cure angle",
            headline_type="D",
            doctor_usage="doctor shown making a health statement, or in medical attire",
            risk="Avoid",
            description="Documented here only so the boundary is explicit: any creative where the "
                         "headline names a disease as the problem the product solves, where the "
                         "product itself is the subject of a cure/treat claim, or where the doctor "
                         "appears in medical attire or is quoted recommending the product.",
            checklist=[
                "NEVER generate this angle.",
                "If a brief asks for this, redirect to broad_wellness_ritual, ingredient_hero, or "
                "consumer_fear_hook instead.",
            ],
            example_headline="(none — banned pattern, not a usable headline)",
        ),
    ]


def feasible_angles(include_avoid: bool = False) -> list[VisualAngle]:
    angles = _angles()
    if include_avoid:
        return angles
    return [a for a in angles if a.risk != "Avoid"]


def render_report(include_avoid: bool = False) -> str:
    rules = load_rules()
    angles = feasible_angles(include_avoid=include_avoid)
    parts = [
        f"{len(angles)} feasible visual angle(s) for {rules['product']['name']} "
        f"(+ {sum(1 for a in _angles() if a.risk == 'Avoid')} documented-but-banned pattern, "
        f"see --include-avoid).",
        "",
    ]
    for a in angles:
        parts.append(f"## {a.name}  [{a.risk}, headline Type {a.headline_type}]")
        parts.append(a.description)
        parts.append("Checklist:")
        parts.extend(f"  - {c}" for c in a.checklist)
        parts.append("")
        parts.append("Prompt:")
        parts.append(a.prompt(rules))
        parts.append("")
        parts.append("-" * 72)
        parts.append("")
    return "\n".join(parts)
