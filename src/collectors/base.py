"""
Base interface for all platform collectors (Reddit, TikTok, Instagram, etc).

Every collector returns a list of dicts in this common shape, so the
normalizer and Sheets writer never need to know which platform a row
came from.
"""
from abc import ABC, abstractmethod
from datetime import datetime

# The common row schema every collector must produce.
# Matches the Google Sheet columns:
#   Timestamp | Collected At | Person/Handle | Platform | Type |
#   Matched Keyword | Content Snippet | URL
ROW_FIELDS = [
    "timestamp",        # when the post/comment was created (ISO string, UTC)
    "author",            # username/handle
    "platform",          # "Reddit", "TikTok", etc.
    "type",              # "Post", "Comment", "Reddit Thread", "Customer Review"
    "matched_keyword",   # which keyword triggered this row
    "content_snippet",   # first ~200 chars of the text
    "url",                # direct link back to source
]


class BaseCollector(ABC):
    """Subclass this for each platform."""

    platform_name: str = "Unknown"

    def __init__(self, keywords: list[str], since: datetime):
        self.keywords = keywords
        self.since = since  # only collect content created after this timestamp

    @abstractmethod
    def collect(self) -> list[dict]:
        """
        Run collection for all keywords and return a list of row dicts
        matching ROW_FIELDS. Must filter out anything older than self.since.
        """
        raise NotImplementedError

    def _make_row(
        self,
        *,
        timestamp: datetime,
        author: str,
        row_type: str,
        matched_keyword: str,
        content: str,
        url: str,
    ) -> dict:
        """Helper so every collector builds rows in the exact same shape."""
        snippet = (content or "").strip().replace("\n", " ")[:200]
        return {
            "timestamp": timestamp.isoformat(),
            "author": author or "[deleted/unknown]",
            "platform": self.platform_name,
            "type": row_type,
            "matched_keyword": matched_keyword,
            "content_snippet": snippet,
            "url": url,
        }