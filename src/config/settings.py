"""
Central configuration loader.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def _require(key):
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value


class Settings:
    REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
    REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")
    REDDIT_SUBREDDITS = os.getenv("REDDIT_SUBREDDITS", "all")
    REDDIT_MAX_RESULTS_PER_KEYWORD = int(os.getenv("REDDIT_MAX_RESULTS_PER_KEYWORD", "50"))
    REDDIT_MAX_COMMENTS_PER_POST = int(os.getenv("REDDIT_MAX_COMMENTS_PER_POST", "30"))

    APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")
    TIKTOK_SEARCH_ACTOR_ID = os.getenv("TIKTOK_SEARCH_ACTOR_ID", "clockworks/tiktok-scraper")
    TIKTOK_HASHTAG_ACTOR_ID = os.getenv("TIKTOK_HASHTAG_ACTOR_ID", "clockworks/tiktok-scraper")
    TIKTOK_COMMENTS_ACTOR_ID = os.getenv("TIKTOK_COMMENTS_ACTOR_ID", "clockworks/tiktok-comments-scraper")
    TIKTOK_TARGET_MATCHES_PER_KEYWORD = int(os.getenv("TIKTOK_TARGET_MATCHES_PER_KEYWORD", "10"))
    TIKTOK_SEARCH_BATCH_SIZE = int(os.getenv("TIKTOK_SEARCH_BATCH_SIZE", "20"))
    TIKTOK_MAX_RAW_RESULTS_PER_KEYWORD = int(os.getenv("TIKTOK_MAX_RAW_RESULTS_PER_KEYWORD", "100"))
    TIKTOK_MAX_COMMENTS_PER_VIDEO = int(os.getenv("TIKTOK_MAX_COMMENTS_PER_VIDEO", "30"))
    TIKTOK_LANGUAGE_FILTER = os.getenv("TIKTOK_LANGUAGE_FILTER", "en") or None
    TIKTOK_LOOKBACK_HOURS = int(os.getenv("TIKTOK_LOOKBACK_HOURS", "2160"))
    TIKTOK_COLLECT_COMMENTS = os.getenv("TIKTOK_COLLECT_COMMENTS", "true").lower() != "false"
    TIKTOK_KEYWORDS_DOCX_PATH = os.getenv("TIKTOK_KEYWORDS_DOCX_PATH", "./data/tiktok_keywords.docx")

    INSTAGRAM_LOOKBACK_DAYS = int(os.getenv("INSTAGRAM_LOOKBACK_DAYS", "1"))
    INSTAGRAM_TARGET_MATCHES_PER_KEYWORD = int(os.getenv("INSTAGRAM_TARGET_MATCHES_PER_KEYWORD", "20"))
    INSTAGRAM_SEARCH_BATCH_SIZE = int(os.getenv("INSTAGRAM_SEARCH_BATCH_SIZE", "20"))
    INSTAGRAM_MAX_RAW_RESULTS_PER_KEYWORD = int(os.getenv("INSTAGRAM_MAX_RAW_RESULTS_PER_KEYWORD", "200"))
    INSTAGRAM_COLLECT_COMMENTS = os.getenv("INSTAGRAM_COLLECT_COMMENTS", "false").lower() == "true"
    INSTAGRAM_LANGUAGE_FILTER = os.getenv("INSTAGRAM_LANGUAGE_FILTER", "en") or None
    INSTAGRAM_KEYWORDS_DOCX_PATH = os.getenv("INSTAGRAM_KEYWORDS_DOCX_PATH", "./data/instagram_keywords.docx")

    GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "./data/service_account.json")
    GOOGLE_SHEET_ID = _require("GOOGLE_SHEET_ID")


settings = Settings()
