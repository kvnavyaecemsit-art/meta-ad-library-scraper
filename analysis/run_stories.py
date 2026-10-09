"""Batch-generates visual stories for scraped ad images and writes them to
output/data/stories.json as {ad_archive_id: story_text}, which the gallery viewer
(output/viewer.html) reads and shows in the ad detail modal.

Usage:
    python -m analysis.run_stories --brand Kapiva --limit 20
    python -m analysis.run_stories                 # all brands, all ads
"""
import argparse
import json
import logging
import time
from pathlib import Path

from .gemini_client import MissingApiKeyError
from .story import analyze_image_story

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
DATA_DIR = OUTPUT_DIR / "data"
STORIES_PATH = DATA_DIR / "stories.json"

logger = logging.getLogger(__name__)


def load_manifest() -> list[dict]:
    manifest_path = DATA_DIR / "manifest.json"
    if not manifest_path.exists():
        return []
    return json.loads(manifest_path.read_text())


def load_stories() -> dict[str, str]:
    if STORIES_PATH.exists():
        return json.loads(STORIES_PATH.read_text())
    return {}


def save_stories(stories: dict[str, str]) -> None:
    STORIES_PATH.write_text(json.dumps(stories, indent=2, ensure_ascii=False))


def iter_ads(brand: str | None) -> list[dict]:
    ads = []
    seen_ids = set()
    for entry in load_manifest():
        if brand and entry["brand"].lower() != brand.lower():
            continue
        path = DATA_DIR / entry["file"]
        if not path.exists():
            continue
        for ad in json.loads(path.read_text()):
            ad_id = ad.get("ad_archive_id")
            if not ad_id or ad_id in seen_ids:
                continue
            seen_ids.add(ad_id)
            ads.append(ad)
    return ads


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Gemini visual-story text for scraped ad images.")
    parser.add_argument("--brand", help="Only process ads for this brand (matches the manifest's brand label).")
    parser.add_argument("--limit", type=int, default=None, help="Max number of ads to process.")
    parser.add_argument("--force", action="store_true", help="Re-generate stories that already exist.")
    parser.add_argument("--sleep", type=float, default=1.0, help="Seconds to sleep between API calls.")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(asctime)s %(message)s")

    ads = iter_ads(args.brand)
    stories = load_stories()

    todo = [ad for ad in ads if args.force or ad["ad_archive_id"] not in stories]
    if args.limit:
        todo = todo[: args.limit]

    print(f"{len(ads)} unique ads found, {len(todo)} to process.")

    done = 0
    for ad in todo:
        images = ad.get("local_image_paths") or []
        if not images:
            continue
        image_path = OUTPUT_DIR / images[0]
        if not image_path.exists():
            logger.warning("Missing image file: %s", image_path)
            continue

        try:
            story = analyze_image_story(image_path)
        except MissingApiKeyError as e:
            print(f"ERROR: {e}")
            return
        except Exception as e:
            logger.warning("Failed on %s (%s): %s", ad["ad_archive_id"], ad.get("page_name"), e)
            continue

        stories[ad["ad_archive_id"]] = story
        done += 1
        print(f"[{done}/{len(todo)}] {ad.get('page_name')}: {story[:80]}...")
        save_stories(stories)  # save incrementally so partial runs aren't lost
        time.sleep(args.sleep)

    print(f"Done. {done} new stories written to {STORIES_PATH}")


if __name__ == "__main__":
    main()
