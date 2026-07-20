"""
Base interface for all platform collectors.
"""
from abc import ABC, abstractmethod
from datetime import datetime


class BaseCollector(ABC):
    platform_name = "Unknown"

    def __init__(self, keywords, since, known_urls=None):
        self.keywords = keywords
        self.since = since
        self.known_urls = known_urls or set()

    @abstractmethod
    def collect(self):
        raise NotImplementedError

    def _make_row(self, *, timestamp, author, row_type, matched_keyword, content, url):
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
