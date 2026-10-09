"""Persists scraped ad records and downloads their media.

Ad metadata is written as JSON today. To move to Supabase later, replace
`save_ads_json` with a function that upserts the same list of dicts into a
table (e.g. `supabase.table("ads").upsert(ads).execute()`) — the record
shape produced by scraper.parser stays the same either way.
"""
import json
import logging
import mimetypes
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def save_ads_json(ads: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(ads, f, indent=2, ensure_ascii=False)
    logger.info("Wrote %d ads to %s", len(ads), path)


def update_manifest(data_dir: Path, entry: dict) -> None:
    """Adds/replaces one run's entry in `data_dir/manifest.json`, the index
    the gallery viewer (viewer.html) reads to list available scrape runs.
    """
    manifest_path = data_dir / "manifest.json"
    manifest = []
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text())
        except json.JSONDecodeError:
            manifest = []

    manifest = [e for e in manifest if e.get("file") != entry["file"]]
    manifest.append(entry)
    manifest.sort(key=lambda e: e.get("scraped_at", ""), reverse=True)

    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    logger.info("Updated %s (%d runs)", manifest_path, len(manifest))


def _download_file(url: str, dest_no_ext: Path, session: requests.Session, timeout: int) -> Path | None:
    try:
        resp = session.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.warning("Failed to download %s: %s", url, e)
        return None

    ext = mimetypes.guess_extension(resp.headers.get("Content-Type", "").split(";")[0]) or ".jpg"
    if ext == ".jpe":
        ext = ".jpg"
    dest = dest_no_ext.with_suffix(ext)
    dest.write_bytes(resp.content)
    return dest


def download_ad_media(
    ad: dict,
    images_dir: Path,
    *,
    download_video_previews: bool = True,
    session: requests.Session | None = None,
    timeout: int = 20,
    path_root: Path | None = None,
    skip_existing: bool = True,
) -> dict:
    """Downloads an ad's images (and video preview thumbnails) to
    `images_dir/<ad_archive_id>/`. Returns the ad dict with a
    `local_image_paths` key added — paths relative to `path_root` when given
    (so they can be used directly as <img src> by a server rooted there),
    otherwise absolute.

    When `skip_existing` is true (the default) and this ad's directory already
    has files in it from a previous run, no network calls are made — the
    existing files are reused as-is. This makes re-running a scrape to
    backfill new ads cheap instead of re-downloading everything already on disk.
    """
    session = session or requests.Session()
    ad_id = ad.get("ad_archive_id") or "unknown"
    ad_dir = images_dir / ad_id

    def _record_path(path: Path) -> str:
        if path_root is not None:
            return str(path.relative_to(path_root))
        return str(path)

    if skip_existing and ad_dir.is_dir():
        existing = sorted(p for p in ad_dir.iterdir() if p.is_file())
        if existing:
            ad["local_image_paths"] = [_record_path(p) for p in existing]
            return ad

    ad_dir.mkdir(parents=True, exist_ok=True)

    local_paths = []

    for i, url in enumerate(ad.get("image_urls", [])):
        path = _download_file(url, ad_dir / f"image_{i}", session, timeout)
        if path:
            local_paths.append(_record_path(path))

    if download_video_previews:
        for i, video in enumerate(ad.get("videos", [])):
            preview_url = video.get("video_preview_image_url")
            if not preview_url:
                continue
            path = _download_file(preview_url, ad_dir / f"video_preview_{i}", session, timeout)
            if path:
                local_paths.append(_record_path(path))

    ad["local_image_paths"] = local_paths
    return ad


def download_all_media(
    ads: list[dict],
    images_dir: Path,
    **kwargs,
) -> list[dict]:
    session = requests.Session()
    for ad in ads:
        download_ad_media(ad, images_dir, session=session, **kwargs)
    return ads
