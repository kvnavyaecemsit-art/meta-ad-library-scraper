"""Loads compliance/rules.yaml (the team-supplied, authoritative ruleset)."""
from functools import lru_cache
from pathlib import Path

import yaml

RULES_PATH = Path(__file__).resolve().parent / "rules.yaml"


@lru_cache(maxsize=1)
def load_rules() -> dict:
    return yaml.safe_load(RULES_PATH.read_text())


def compliance_brief(rules: dict | None = None) -> str:
    """A compact, prompt-sized summary of rules.yaml for grounding an LLM's
    reasoning about whether a competitor creative pattern is reusable for our
    product. Not a substitute for compliance.validate — this is for creative
    ideation context, not a pass/fail check."""
    rules = rules or load_rules()
    p = rules["product"]
    approved = rules["approved_ingredient_claims"]

    lines = [
        f"Our product: {p['name']} ({p['brand']}), {p['type']}, {p['pack']} at "
        f"₹{p['price_inr']} (₹{p['per_day_inr']}/day). Formulated by {p['formulator']}. "
        f"Key herbs: {', '.join(p['key_herbs'])}.",
        "",
        "Hard constraints when judging if a competitor's creative pattern could work for us:",
        f"- Banned verbs (never use): {', '.join(rules['verbs']['banned'])}.",
        f"- Allowed verbs: {', '.join(rules['verbs']['allowed'])}.",
        "- Disease terms must be substituted with wellness framing: " + "; ".join(
            f"\"{k}\" -> \"{v}\"" for k, v in rules["disease_terms"].items()
        ) + ".",
        "- No outcome-timeline claims (e.g. \"in 30 days\", \"results in 2 months\") of any kind.",
        "- The doctor's name may only appear as a factual authorship attribution "
        f"(e.g. \"{rules['doctor']['allowed_patterns'][0]}\") — never as a recommendation/endorsement "
        f"(never with words like {', '.join(rules['doctor']['banned_near_name'][:4])}, etc).",
        "- Any ingredient claim must match one of these pre-approved claims (or be flagged as needing "
        "legal review): " + "; ".join(
            claim for spec in approved.values() for claim in spec["claims"]
        ) + ".",
        "- A disease/cure/prevent-shaped headline (Type D) is always banned, regardless of visual treatment.",
    ]
    return "\n".join(lines)
