"""Batch-generates the creative-strategy breakdown (analysis/creative_analysis.py)
for a sample of scraped ads and writes output/data/creative_analysis.json as
{ad_archive_id: {...}}, read by output/creative_review.html.

Usage:
    python -m analysis.run_creative_analysis --count 10
    python -m analysis.run_creative_analysis --count 10 --brand Kapiva
"""
import argparse
import json
import logging
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .gemini_client import MissingApiKeyError
from .creative_analysis import analyze_ad_creative

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
DATA_DIR = OUTPUT_DIR / "data"
RESULTS_PATH = DATA_DIR / "creative_analysis.json"

logger = logging.getLogger(__name__)


def load_manifest() -> list[dict]:
    manifest_path = DATA_DIR / "manifest.json"
    if not manifest_path.exists():
        return []
    return json.loads(manifest_path.read_text())


def load_ads_by_brand(brand_filter: str | None) -> dict[str, list[dict]]:
    """Returns {brand: [unique ads]} — merges all runs for a brand, dedup by ad_archive_id."""
    by_brand: dict[str, dict[str, dict]] = {}
    for entry in load_manifest():
        if brand_filter and entry["brand"].lower() != brand_filter.lower():
            continue
        path = DATA_DIR / entry["file"]
        if not path.exists():
            continue
        bucket = by_brand.setdefault(entry["brand"], {})
        for ad in json.loads(path.read_text()):
            ad_id = ad.get("ad_archive_id")
            if ad_id and ad_id not in bucket:
                bucket[ad_id] = ad
    return {brand: list(ads.values()) for brand, ads in by_brand.items()}


def pick_sample(count: int, brand_filter: str | None) -> list[dict]:
    """Picks a diverse sample: spread across brands, preferring each brand's
    official/primary page (its most common page_name) over keyword-match noise."""
    by_brand = load_ads_by_brand(brand_filter)
    if not by_brand:
        return []

    brands = list(by_brand.keys())
    per_brand = max(1, count // len(brands))

    sample = []
    for brand in brands:
        ads = by_brand[brand]
        page_counts = Counter(a.get("page_name") for a in ads)
        primary_page = page_counts.most_common(1)[0][0]
        primary_ads = [
            a for a in ads
            if a.get("page_name") == primary_page
            and a.get("local_image_paths")
            and "{{" not in (a.get("title") or "")
            and "{{" not in (a.get("body_text") or "")
        ]
        sample.extend(primary_ads[:per_brand])

    return sample[:count]


def running_days(ad: dict) -> int | None:
    start = ad.get("start_date")
    if not start:
        return None
    try:
        start_dt = datetime.fromisoformat(start)
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - start_dt).days


def ad_library_url(ad: dict) -> str:
    return f"https://www.facebook.com/ads/library/?id={ad.get('ad_archive_id')}"


def load_results() -> dict:
    if RESULTS_PATH.exists():
        return json.loads(RESULTS_PATH.read_text())
    return {}


def save_results(results: dict) -> None:
    RESULTS_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate creative-strategy breakdowns for sampled ads.")
    parser.add_argument("--count", type=int, default=10, help="How many ads to analyze. Default: 10")
    parser.add_argument("--brand", help="Restrict the sample to one brand.")
    parser.add_argument("--force", action="store_true", help="Re-generate ads that already have results.")
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(asctime)s %(message)s")

    sample = pick_sample(args.count, args.brand)
    results = load_results()
    todo = [ad for ad in sample if args.force or ad["ad_archive_id"] not in results]

    print(f"Sampled {len(sample)} ads, {len(todo)} to analyze.")

    done = 0
    for ad in todo:
        image_path = OUTPUT_DIR / ad["local_image_paths"][0]
        if not image_path.exists():
            logger.warning("Missing image for %s: %s", ad["ad_archive_id"], image_path)
            continue

        try:
            analysis = analyze_ad_creative(ad, image_path)
        except MissingApiKeyError as e:
            print(f"ERROR: {e}")
            return
        except Exception as e:
            logger.warning("Failed on %s (%s): %s", ad["ad_archive_id"], ad.get("page_name"), e)
            continue

        results[ad["ad_archive_id"]] = {
            **analysis,
            "ad_archive_id": ad["ad_archive_id"],
            "brand": ad.get("brand"),
            "page_name": ad.get("page_name"),
            "title": ad.get("title"),
            "body_text": ad.get("body_text"),
            "cta_text": ad.get("cta_text"),
            "local_image_paths": ad.get("local_image_paths"),
            "collation_count": ad.get("collation_count"),
            "running_days": running_days(ad),
            "ad_library_url": ad_library_url(ad),
        }
        done += 1
        print(f"[{done}/{len(todo)}] {ad.get('page_name')}: {analysis['creative_root']}")
        save_results(results)
        time.sleep(args.sleep)

    print(f"Done. {done} new analyses written to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
