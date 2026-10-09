# Legal opinion summary — RMP advertising restrictions

Source: `260630_BCT_Final Opinion_APP.pdf` (AP & Partners Advocates, opinion for Blue Cow
Technologies Pvt Ltd, 30 June 2026). Privileged and confidential — internal reference only, do not
redistribute outside the team. Condensed to the parts that drive `visual_angles.py`; see the source
PDF for full reasoning, citations, and qualifications.

Dr. Bimal Chhajer, MBBS MD, is a **modern-medicine practitioner governed by the IMC Regulations**
(Indian Medical Council (Professional Conduct, Etiquette and Ethics) Regulations, 2002). Only the
IMC column of the opinion's Annexure A applies to him — the NCH (homoeopathy) and AYUSH columns
do not.

## The two core restrictions on the RMP (not on BCT/Jaadu Diet directly)

1. **Self-aggrandisement** — an RMP can't use their name/photo/credentials in a way that draws
   attention to their professional position, skill, qualifications, achievements or affiliations.
   Lower risk when the RMP is identified only as a factual formulator and the product stays the
   focus; higher risk when the RMP's qualifications, experience, patient numbers or success rates
   are prominently featured.
2. **Endorsement** — an RMP can't lend their professional authority to approve/recommend/certify a
   commercial product. A truthful "I formulated this" attribution is different from an endorsement
   and is more defensible — the line is *inducing purchase via professional authority* (banned) vs.
   *factual attribution of authorship* (defensible).

Consequence for BCT/Jaadu Diet is indirect but real: if Dr. Bimal is found in breach, the product
may need to be repackaged/recalled and the equity arrangement may need to be restructured.

## Annexure A — IMC column (feasibility of RMP identity use)

| Activity | IMC verdict |
|---|---|
| Photo of practitioner (no medical attire) in advertising | Yes, but contestable — other practitioners/state council could take a contrary view; litigation risk |
| Photo of practitioner (no medical attire) **on packaging** | Permissible but not recommended long-term |
| Practitioner in medical attire (stethoscope, lab coat) anywhere | **No** |
| Practitioner's trademarked animated avatar | **Yes** — defensible as a registered trademark |
| Practitioner's name + title only (no photo) + "formulated by Dr X" | **Yes** — recommended default |
| Practitioner's photograph + authorship attribution | Yes, not in medical attire; the more it reads as "formulator," the better |
| Practitioner's animated avatar + authorship attribution | Yes, same logic as avatar alone |
| TV/video ad featuring the practitioner with the product | Yes, but scale use carries indirect self-aggrandisement risk |

## Annexure B — operative Do's

1. Use the RMP's name and title, not combined with product efficacy claims on the same creative.
2. Attribute authorship: *Formulated by Dr. Bimal Chhajer* / *Dr. Bimal's formulation*.
3. Where the RMP's name is a registered trademark ("Dr. Bimal's"), use it with ™/® wherever it
   appears.
4. Keep the *Jaadu Diet* trademark separate from product names — products sell under the
   *Dr. Bimal's* range, not as "Jaadu Diet [product]".
5. Disclose the material connection (equity/options) on the website, product page, and as a printed
   packaging insert.
6. Health claims only where substantiated by evidence, mapped in a claims file.
7. Photo/video/likeness of the RMP: non-medical attire only, product remains the focus, preferably
   paired with an authorship attribution.

## Annexure B — operative Don'ts

1. No RMP photo in medical attire / lab coat / stethoscope, anywhere.
2. No *doctor recommended*, *doctor approved*, *cardiologist certified*, *expert formulated*,
   *professional grade* language anywhere (label, product page, review title, ad).
3. No *Jaadu Diet [product name]* as a product-level identifier.
4. No *reversing heart disease* / *cure* / *treat* language for any condition.
5. No display of Dr. Bimal's credentials (MBBS, MD, "30+ years") as endorsement badges next to buy
   buttons.
6. No anecdotal/clinic-based patient feedback as substantiation.
7. No superlative practitioner statistics ("600,000+ patients treated", "India's leading
   cardiologist").
8. No implication — via layout, icons, badges, seals, hashtags, or influencer scripts — that the
   product is doctor-recommended/approved/clinically validated.

## Other regimes referenced (apply to BCT/Jaadu Diet directly, not just the RMP)

- **FSSAI Advertising Regulations, Reg 10**: nutraceutical labels can't imply practitioner
  recommendation/approval — reinforces Don't #2 above independently of the RMP's own conduct.
  Regulation 7: health claims need the physiological-role + composition elements and, where a
  benefit is attributed directly to the product, statistically significant published human-study
  evidence.
- **DMR Act**: bans advertising that suggests a product diagnoses/cures/mitigates/treats/prevents a
  Scheduled disease/condition. "Aids weight loss" / "improves heart health" type wellness framing is
  fine; "treats cardiovascular disease" or "reduces blockage to zero" is not. This is the legal
  basis for the ruleset's banned-verb and disease-term-substitution rules.
- **CCPA Guidelines**: the equity/option arrangement with Dr. Bimal is a "material connection" and
  must be disclosed (see Do #5).
- **Self-declaration requirement** (*Indian Medical Association v Union of India*): every ad needs a
  self-declaration certificate filed before publication — an operational/legal step, not a creative
  constraint, but worth flagging downstream of this tool.

## How this maps onto `rules.yaml` and `visual_angles.py`

- `rules.yaml`'s `headline_types` A–D operationalise the self-aggrandisement/endorsement distinction
  above: Type A (broad wellness) and Type C (ingredient-attributed) keep the product/ingredient as
  subject, matching the "factual attribution, product stays focus" standard the opinion treats as
  defensible. Type D (disease name as the headline problem, or the product/doctor making a health
  statement) is exactly the pattern the opinion flags as high-risk self-aggrandisement/endorsement/
  DMR Act exposure, so it's banned outright regardless of who is shown.
- `doctor.banned_near_name` operationalises the endorsement restriction at the copy level: "Dr
  Bimal *recommends*/*approved*" reads as endorsement; "*Formulated by* Dr Bimal" reads as
  attribution.
- The Annexure A IMC column is the source for which **visual treatments of the doctor** (`visual_angles.py`)
  are offered as Safe vs Conditional vs Avoid.
