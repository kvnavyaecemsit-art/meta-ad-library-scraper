import argparse
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

from .browser import scrape_ads
from .storage import download_all_media, save_ads_json, update_manifest
from .urls import build_search_url

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape the Meta Ad Library.")
    search_group = parser.add_mutually_exclusive_group(required=True)
    search_group.add_argument("--keyword", help="Search ads by keyword text.")
    search_group.add_argument("--page-id", help="Search ads by Facebook Page ID.")

    parser.add_argument("--country", default="ALL", help="Two-letter country code, or ALL. Default: ALL")
    parser.add_argument(
        "--active-status", default="active", choices=["active", "inactive", "all"],
        help="Ad status filter. Default: active",
    )
    parser.add_argument("--max-ads", type=int, default=200, help="Max ads to collect. Default: 200")
    parser.add_argument("--brand", help="Friendly brand label for the gallery viewer. Defaults to the keyword/page-id.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output directory.")
    parser.add_argument("--no-images", action="store_true", help="Skip downloading images/video previews.")
    parser.add_argument(
        "--images-only", action="store_true",
        help="Only collect image-format ads (stills/memes) — drops any ad that has video content.",
    )
    parser.add_argument("--headed", action="store_true", help="Run the browser with a visible window (for debugging).")
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser.parse_args()


async def run(args: argparse.Namespace) -> None:
    url = build_search_url(
        keyword=args.keyword,
        page_id=args.page_id,
        country=args.country,
        active_status=args.active_status,
    )

    # Facebook's own media_type=image filter is too aggressive (it excludes
    # legitimate image-only DCO/DPA-format ads), so we always fetch "all"
    # and filter client-side instead: keep only ads with at least one image
    # and zero video content. That means fetching more than max_ads to have
    # enough left after filtering.
    fetch_target = args.max_ads * 4 if args.images_only else args.max_ads
    ads = await scrape_ads(url, max_ads=fetch_target, headless=not args.headed)
    print(f"Collected {len(ads)} ads.")

    if args.images_only:
        before = len(ads)
        ads = [ad for ad in ads if ad.get("image_urls") and not ad.get("videos")]
        ads = ads[: args.max_ads]
        print(f"Filtered to {len(ads)} image-only ads (dropped {before - len(ads)} with video/no media).")

    brand_label = args.brand or args.keyword or f"page_{args.page_id}"
    for ad in ads:
        ad["brand"] = brand_label

    if not args.no_images:
        images_dir = args.out_dir / "images"
        ads = download_all_media(ads, images_dir, path_root=args.out_dir)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_label = "".join(c if c.isalnum() else "_" for c in brand_label)[:50]
    data_dir = args.out_dir / "data"
    out_file = f"{safe_label}_{timestamp}.json"
    save_ads_json(ads, data_dir / out_file)
    update_manifest(data_dir, {
        "file": out_file,
        "brand": brand_label,
        "count": len(ads),
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    })
    print(f"Saved ad data to {data_dir / out_file}")


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
