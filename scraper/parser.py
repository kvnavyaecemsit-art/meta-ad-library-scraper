"""Extracts flat ad records from the raw Ad Library GraphQL JSON."""
from datetime import datetime, timezone
from typing import Any, Iterator


def _to_iso(ts: int | None) -> str | None:
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def find_connections(obj: Any) -> Iterator[dict[str, Any]]:
    """Recursively find every `search_results_connection` dict inside a JSON blob.

    Facebook embeds the first page of results in a deeply nested `data-sjs`
    script tag, and later pages arrive as GraphQL XHR bodies with a different
    (shallower) nesting. Walking the tree for this key works for both without
    depending on the exact wrapper structure, which Facebook changes often.
    """
    if isinstance(obj, dict):
        conn = obj.get("search_results_connection")
        if isinstance(conn, dict) and "edges" in conn:
            yield conn
        for value in obj.values():
            yield from find_connections(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from find_connections(item)


def iter_edges(connection: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Yield each result edge's node from one search_results_connection dict."""
    for edge in connection.get("edges", []):
        yield edge.get("node", {})


def parse_node(node: dict[str, Any]) -> list[dict[str, Any]]:
    """A node can bundle several collated ad variants; return one record each."""
    records = []
    for cr in node.get("collated_results", []):
        snapshot = cr.get("snapshot") or {}
        body = snapshot.get("body") or {}

        images = [
            img.get("original_image_url") or img.get("resized_image_url")
            for img in snapshot.get("images", [])
            if img.get("original_image_url") or img.get("resized_image_url")
        ]
        videos = [
            {
                "video_hd_url": v.get("video_hd_url"),
                "video_preview_image_url": v.get("video_preview_image_url"),
            }
            for v in snapshot.get("videos", [])
        ]

        # DPA / CAROUSEL / DCO ads carry their media per-card instead of in
        # the top-level images/videos lists.
        for card in snapshot.get("cards", []):
            image_url = card.get("original_image_url") or card.get("resized_image_url")
            if image_url:
                images.append(image_url)
            if card.get("video_hd_url"):
                videos.append({
                    "video_hd_url": card.get("video_hd_url"),
                    "video_preview_image_url": card.get("video_preview_image_url"),
                })

        records.append({
            "ad_archive_id": cr.get("ad_archive_id"),
            "collation_id": cr.get("collation_id"),
            "collation_count": cr.get("collation_count"),
            "is_active": cr.get("is_active"),
            "page_id": cr.get("page_id"),
            "page_name": snapshot.get("page_name") or cr.get("page_name"),
            "page_profile_uri": snapshot.get("page_profile_uri"),
            "page_like_count": snapshot.get("page_like_count"),
            "page_categories": snapshot.get("page_categories"),
            "start_date": _to_iso(cr.get("start_date")),
            "end_date": _to_iso(cr.get("end_date")),
            "total_active_time": cr.get("total_active_time"),
            "publisher_platform": cr.get("publisher_platform"),
            "categories": cr.get("categories"),
            "spend": cr.get("spend"),
            "currency": cr.get("currency"),
            "reach_estimate": cr.get("reach_estimate"),
            "display_format": snapshot.get("display_format"),
            "title": snapshot.get("title"),
            "body_text": body.get("text"),
            "caption": snapshot.get("caption"),
            "link_url": snapshot.get("link_url"),
            "link_description": snapshot.get("link_description"),
            "cta_text": snapshot.get("cta_text"),
            "cta_type": snapshot.get("cta_type"),
            "image_urls": images,
            "videos": videos,
        })
    return records


def parse_json_blob(blob: Any) -> list[dict[str, Any]]:
    """Flatten every search_results_connection found in a parsed JSON blob."""
    records = []
    for conn in find_connections(blob):
        for node in iter_edges(conn):
            records.extend(parse_node(node))
    return records
