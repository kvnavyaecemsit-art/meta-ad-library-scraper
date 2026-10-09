"""Builds Meta Ad Library search-page URLs for the two supported search modes."""
from urllib.parse import urlencode

BASE_URL = "https://www.facebook.com/ads/library/"


def build_search_url(
    *,
    keyword: str | None = None,
    page_id: str | None = None,
    country: str = "ALL",
    active_status: str = "active",
    ad_type: str = "all",
    media_type: str = "all",
) -> str:
    """Build a search URL. Pass either `keyword` or `page_id` (not both)."""
    if bool(keyword) == bool(page_id):
        raise ValueError("Pass exactly one of keyword or page_id")

    params = {
        "active_status": active_status,
        "ad_type": ad_type,
        "country": country,
        "media_type": media_type,
    }

    if keyword:
        params.update({
            "q": keyword,
            "search_type": "keyword_unordered",
        })
    else:
        params.update({
            "view_all_page_id": page_id,
            "search_type": "page",
        })

    return f"{BASE_URL}?{urlencode(params)}"
