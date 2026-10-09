# Meta Ad Library Scraper

Scrapes ads from the public [Meta Ad Library](https://www.facebook.com/ads/library/) web UI by
driving a headless browser (Playwright) and intercepting the JSON that Facebook's own frontend
loads (embedded page data + GraphQL responses), rather than parsing obfuscated HTML.

This uses the public web UI, not Meta's official Ad Library API — it's not authorized by Meta's
Terms of Service, so use it for personal research at your own risk. It also has no access token
requirement, and works for regular commercial ads (the official API is really only needed for the
extra fields exposed on political/issue ads).

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

## Usage

Search by keyword:

```bash
python -m scraper.cli --keyword "nike" --country US --max-ads 200
```

Search by advertiser (Facebook Page ID):

```bash
python -m scraper.cli --page-id 89516513179 --active-status all --max-ads 200
```

Options:

| Flag | Description | Default |
|---|---|---|
| `--keyword` | Search by keyword text (mutually exclusive with `--page-id`) | — |
| `--page-id` | Search by Facebook Page ID (mutually exclusive with `--keyword`) | — |
| `--country` | Two-letter country code, or `ALL` | `ALL` |
| `--active-status` | `active`, `inactive`, or `all` | `active` |
| `--max-ads` | Max unique ads to collect | `200` |
| `--out-dir` | Output directory | `./output` |
| `--no-images` | Skip downloading images/video previews | off |
| `--headed` | Run with a visible browser window (debugging) | off |
| `-v` | Verbose logging | off |

## Output

- `output/data/<label>_<timestamp>.json` — one JSON array of ad records.
- `output/images/<ad_archive_id>/` — downloaded images and video preview thumbnails for each ad.

Each ad record includes: `ad_archive_id`, `page_id`, `page_name`, `start_date`, `end_date`,
`is_active`, `publisher_platform`, `display_format`, `title`, `body_text`, `cta_text`, `link_url`,
`image_urls`, `videos`, and (after download) `local_image_paths`.

Full video files are not downloaded by default — only video preview thumbnails — since videos can
be large. To fetch full videos, download the `video_hd_url` from each ad's `videos` list yourself.

## Moving to Supabase later

`scraper/storage.py` is the only place that knows how ad records get persisted. Swap
`save_ads_json` for a function that upserts the same list of dicts into a Supabase table
(e.g. `supabase.table("ads").upsert(ads).execute()`), and point image downloads at Supabase
Storage instead of the local `output/images/` folder — the record shape produced by
`scraper/parser.py` doesn't need to change.

## How it works

1. `scraper/urls.py` builds a Meta Ad Library search URL for a keyword or Page ID.
2. `scraper/browser.py` opens the page in Playwright, pulls the first batch of results out of an
   embedded `<script type="application/json">` tag, then repeatedly scrolls and intercepts the
   GraphQL XHR responses that load more results, until enough ads are collected or scrolling
   stops turning up new ones.
3. `scraper/parser.py` recursively finds every `search_results_connection` object in that JSON
   (regardless of how it's nested) and flattens each ad into a plain dict.
4. `scraper/storage.py` downloads each ad's images/video-preview thumbnails and writes the ad
   records to JSON.

## Notes / limitations

- This depends on Facebook's internal JSON shape, which can change without notice — if it stops
  working, the fix is almost always small adjustments to `scraper/parser.py`.
- Facebook may show a cookie-consent banner or CAPTCHA depending on IP/locale; the scraper tries
  to auto-dismiss a cookie banner but does not solve CAPTCHAs. Run with `--headed` to see what's
  happening if a scrape returns 0 ads.
- Scraping is rate-limit sensitive — avoid very high `--max-ads` / concurrent runs from the same IP.

## Gallery viewer

`output/viewer.html` is a static page (no build step) that browses every scraped run. Serve the
`output/` folder and open it:

```bash
cd output && python3 -m http.server 8765
# open http://localhost:8765/viewer.html
```

It reads `output/data/manifest.json` (written automatically by every scrape) plus, if present,
`output/data/stories.json` (written by the Gemini story analyzer below) to show each ad's inferred
visual story in the detail modal.

## Gemini image-story analysis (`analysis/`)

Given an ad image, `analysis/story.py` asks Gemini to read the image top-to-bottom and write the
underlying marketing story as a short first-person "product voice" monologue (matching the style
the team specified — e.g. *"I am your secret to inner radiance, a premium collagen powder..."*).

Setup: put `GEMINI_API_KEY=<your key>` in `.env` at the project root (get a key from
[Google AI Studio](https://aistudio.google.com/)).

Batch-run it over already-scraped ads:

```bash
python -m analysis.run_stories --brand Kapiva --limit 20   # one brand, capped
python -m analysis.run_stories                              # every scraped ad
```

Results are written incrementally to `output/data/stories.json` as `{ad_archive_id: story_text}`,
which `viewer.html` picks up automatically on refresh.

## Ad-compliance tool (`compliance/`) — Dr. Bimal's Arjuna Cardio Care Tea

A separate, deterministic (non-LLM) tool for planning and checking ad creative for the Jaadu Diet
product, built from:

- `compliance/rules.yaml` — the team-authoritative ruleset (banned verbs, disease-term substitutions,
  approved ingredient claims, headline-type taxonomy, disclaimer rules, doctor-attribution patterns).
- `compliance/legal_opinion_summary.md` — condensed from the attached legal opinion
  (`260630_BCT_Final Opinion_APP.pdf`, AP & Partners, 30 June 2026), specifically the Annexure A
  "Modern medicine (IMC)" feasibility table and Annexure B Do's/Don'ts, since Dr. Bimal Chhajer is
  an IMC-governed (not AYUSH/homoeopathy) practitioner. **Privileged/confidential — internal use only.**

List feasible visual angles + ready-to-use image-generation prompts for each:

```bash
python -m compliance.cli angles              # text report
python -m compliance.cli angles --json        # machine-readable
python -m compliance.cli angles --include-avoid  # also show the documented banned pattern
```

Validate a specific headline/body against the ruleset:

```bash
python -m compliance.cli validate --headline "Arjuna Chhal helps reduce bad cholesterol" \
  --body "Formulated by Dr. Bimal Chhajer MBBS MD."
```

This is a first-pass automated screen, not legal sign-off — see the qualifications in the source
opinion PDF. Anything it flags `[FAIL]` should be rewritten; anything `[WARN]` needs a human look.
