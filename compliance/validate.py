"""Validates ad copy against compliance/rules.yaml.

This is a deterministic, auditable checker — not an LLM judgment call — because the
cost of a false "compliant" here is a real regulatory/legal exposure (see
compliance/legal_opinion_summary.md). It flags likely violations; it does not
replace legal review, and it does not catch violations expressed only in imagery
(e.g. an RMP photo in a lab coat) since it only reads text.
"""
import re
from dataclasses import dataclass
from typing import Literal

from .rules import load_rules

Severity = Literal["fail", "warn"]


@dataclass
class Finding:
    rule: str
    severity: Severity
    message: str


def _word_pattern(word: str) -> re.Pattern:
    # Multi-word phrases ("clinically proven") match as a literal substring;
    # single words match on word boundaries so "control" doesn't hit "controller".
    if " " in word:
        return re.compile(re.escape(word), re.IGNORECASE)
    return re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)


def _known_safe_phrases(rules: dict) -> list[str]:
    """Fixed disclaimer text and pre-approved ingredient-claim strings: these are
    allowed to contain words that would otherwise be flagged (the disclaimer itself
    says "not intended to ... treat, cure or prevent"; approved claims name the
    disease term they're attributed to, e.g. "cholesterol"). Strip them before
    scanning for violations so they don't self-trigger."""
    phrases = [rules["disclaimer"]["text_en"], rules["disclaimer"]["text_hi"]]
    for spec in rules["approved_ingredient_claims"].values():
        phrases.extend(spec["claims"])
    return [p for p in phrases if p]


def _sanitize_for_scanning(text: str, rules: dict) -> str:
    for phrase in _known_safe_phrases(rules):
        text = re.sub(re.escape(phrase), "", text, flags=re.IGNORECASE)
    return text


def check_banned_verbs(text: str, rules: dict) -> list[Finding]:
    findings = []
    for verb in rules["verbs"]["banned"]:
        if _word_pattern(verb).search(text):
            findings.append(Finding(
                "banned_verb", "fail",
                f"Banned verb/phrase \"{verb}\" found — these imply a medical claim a food product can't make.",
            ))
    for verb in rules["verbs"].get("banned_hindi", []):
        if verb in text:
            findings.append(Finding("banned_verb_hindi", "fail", f"Banned Hindi verb \"{verb}\" found."))
    return findings


def check_disease_terms(text: str, rules: dict) -> list[Finding]:
    findings = []
    for term, substitute in rules["disease_terms"].items():
        if _word_pattern(term).search(text):
            findings.append(Finding(
                "disease_term", "fail",
                f"Disease term \"{term}\" found — use the approved wellness substitute \"{substitute}\" instead.",
            ))
    for term, substitute in rules.get("disease_terms_hindi", {}).items():
        if term in text:
            findings.append(Finding(
                "disease_term_hindi", "fail",
                f"Disease term \"{term}\" found — use the approved substitute \"{substitute}\" instead.",
            ))
    return findings


def check_timeline_claims(text: str, rules: dict) -> list[Finding]:
    findings = []
    for pattern in rules["timeline_patterns"]:
        if re.search(pattern, text, re.IGNORECASE):
            findings.append(Finding(
                "timeline_claim", "fail",
                f"Outcome-timeline language matched pattern /{pattern}/ — specific-timeline outcome claims are always banned for this product.",
            ))
    return findings


def check_doctor_usage(text: str, rules: dict) -> list[Finding]:
    findings = []
    doctor = rules["doctor"]
    names_present = [n for n in doctor["names"] if n.lower() in text.lower()]
    if not names_present:
        return findings

    for line in text.splitlines():
        line_lower = line.lower()
        if not any(n.lower() in line_lower for n in names_present):
            continue
        for banned in doctor["banned_near_name"]:
            if banned.lower() in line_lower:
                findings.append(Finding(
                    "doctor_endorsement_language", "fail",
                    f"\"{banned}\" appears on the same line as the doctor's name — this reads as an endorsement, "
                    f"not an authorship attribution. Use one of the allowed patterns instead, e.g. "
                    f"\"{doctor['allowed_patterns'][0]}\".",
                ))

    allowed_hit = any(p.lower() in text.lower() for p in doctor["allowed_patterns"])
    if not allowed_hit:
        findings.append(Finding(
            "doctor_attribution_missing", "warn",
            "The doctor's name is used, but no approved attribution pattern (e.g. \"Formulated by Dr. Bimal "
            "Chhajer MBBS MD\") was found — confirm the copy frames this as authorship, not endorsement.",
        ))
    return findings


def check_ingredient_claims(text: str, rules: dict) -> list[Finding]:
    """Flags health-benefit-shaped sentences about an ingredient that aren't on the approved list."""
    findings = []
    approved = rules["approved_ingredient_claims"]
    text_lower = text.lower()
    claim_verb_pattern = re.compile(r"\b(" + "|".join(re.escape(v) for v in rules["verbs"]["allowed"]) + r")\b", re.IGNORECASE)

    for ingredient, spec in approved.items():
        aliases_present = [a for a in spec["aliases"] if a.lower() in text_lower]
        if not aliases_present:
            continue
        approved_claims_lower = [c.lower() for c in spec["claims"]]
        for line in text.splitlines():
            line_lower = line.lower()
            if not any(a.lower() in line_lower for a in aliases_present):
                continue
            if not claim_verb_pattern.search(line):
                continue  # ingredient is just mentioned, not making a claim
            if not any(c in line_lower for c in approved_claims_lower):
                findings.append(Finding(
                    "unapproved_ingredient_claim", "warn",
                    f"\"{line.strip()}\" makes a claim about {ingredient} that doesn't match one of the pre-approved "
                    f"claim strings in rules.yaml. Either use an approved claim verbatim or get this specific "
                    f"wording legally reviewed before use.",
                ))
    return findings


def classify_headline(headline: str, rules: dict) -> str:
    """Best-effort heuristic classification into headline_types A-D. Not authoritative —
    a human should confirm Type D exclusions especially, since a false 'not-D' is the
    costly failure mode here."""
    approved_claims_lower = {
        c.lower() for spec in rules["approved_ingredient_claims"].values() for c in spec["claims"]
    }
    if headline.strip().lower() in approved_claims_lower:
        return "C"

    scan_headline = _sanitize_for_scanning(headline, rules)
    text_lower = scan_headline.lower()

    disease_hit = any(_word_pattern(t).search(scan_headline) for t in rules["disease_terms"]) or \
        any(t in scan_headline for t in rules.get("disease_terms_hindi", {}))
    doctor_hit = any(n.lower() in text_lower for n in rules["doctor"]["names"])
    banned_verb_hit = any(_word_pattern(v).search(scan_headline) for v in rules["verbs"]["banned"])
    if disease_hit or banned_verb_hit or doctor_hit:
        return "D"

    ingredient_hit = any(
        alias.lower() in text_lower
        for spec in rules["approved_ingredient_claims"].values()
        for alias in spec["aliases"]
    )
    allowed_verb_hit = any(_word_pattern(v).search(scan_headline) for v in rules["verbs"]["allowed"])
    if ingredient_hit and allowed_verb_hit:
        return "C"

    if "?" in headline:
        return "B"

    return "A"


def disclaimer_required(headline_type: str, headline: str, body_text: str, rules: dict) -> bool:
    """Per rules.yaml `disclaimer.required_unless`: exempt if the headline is Type A
    with no disease terms anywhere, OR every claim in the body is ingredient-attributed
    with no disease terms anywhere. Interpreted conservatively (AND within each
    exemption path) since an unnecessary disclaimer costs nothing but a missing one is
    a real violation."""
    disease_free = not (
        check_disease_terms(_sanitize_for_scanning(body_text, rules), rules)
        or check_disease_terms(_sanitize_for_scanning(headline, rules), rules)
    )
    if headline_type == "A" and disease_free:
        return False
    if headline_type == "C" and disease_free:
        return False
    return True


def validate_copy(headline: str, body: str = "", rules: dict | None = None) -> list[Finding]:
    rules = rules or load_rules()
    full_text = f"{headline}\n{body}"
    scan_text = _sanitize_for_scanning(full_text, rules)

    findings: list[Finding] = []
    findings += check_banned_verbs(scan_text, rules)
    findings += check_disease_terms(scan_text, rules)
    findings += check_timeline_claims(scan_text, rules)
    findings += check_doctor_usage(full_text, rules)
    findings += check_ingredient_claims(full_text, rules)

    headline_type = classify_headline(headline, rules)
    if headline_type == "D":
        findings.append(Finding(
            "headline_type_d", "fail",
            f"Headline \"{headline}\" classifies as Type D (banned): it names a disease, the doctor, or a banned "
            f"verb as the headline subject. Rewrite as Type A (broad wellness), B (consumer-fear question), or "
            f"C (ingredient claim).",
        ))

    if disclaimer_required(headline_type, headline, body, rules) and rules["disclaimer"]["text_en"] not in body:
        findings.append(Finding(
            "disclaimer_missing", "warn",
            f"This copy likely requires the disclaimer per rules.yaml: \"{rules['disclaimer']['text_en']}\"",
        ))

    return findings


def format_findings(findings: list[Finding]) -> str:
    if not findings:
        return "No issues found."
    lines = []
    for f in findings:
        tag = "FAIL" if f.severity == "fail" else "WARN"
        lines.append(f"[{tag}] {f.rule}: {f.message}")
    return "\n".join(lines)
