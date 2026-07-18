"""
Main entry point.
"""
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config.settings import settings
from keyword_extractor import extract_keywords
from sheets_writer import SheetsWriter
from collectors.tiktok_collector import TikTokCollector
from collectors.instagram_collector import InstagramCollector

LOGS_DIR = Path(__file__).resolve().parents[1] / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
_log_filename = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOGS_DIR / _log_filename, encoding="utf-8")],
)
logger = logging.getLogger("main")


def build_tiktok_collector(keywords, since):
    return TikTokCollector(
        keywords=keywords, since=since, apify_token=settings.APIFY_API_TOKEN,
        search_actor_id=settings.TIKTOK_SEARCH_ACTOR_ID,
        hashtag_actor_id=settings.TIKTOK_HASHTAG_ACTOR_ID,
        comments_actor_id=settings.TIKTOK_COMMENTS_ACTOR_ID,
        target_matches_per_keyword=settings.TIKTOK_TARGET_MATCHES_PER_KEYWORD,
        search_batch_size=settings.TIKTOK_SEARCH_BATCH_SIZE,
        max_raw_results_per_keyword=settings.TIKTOK_MAX_RAW_RESULTS_PER_KEYWORD,
        max_comments_per_video=settings.TIKTOK_MAX_COMMENTS_PER_VIDEO,
        language_filter=settings.TIKTOK_LANGUAGE_FILTER,
        collect_comments=settings.TIKTOK_COLLECT_COMMENTS,
    )


def build_instagram_collector(keywords, since):
    return InstagramCollector(
        keywords=keywords, since=since, apify_token=settings.APIFY_API_TOKEN,
        target_matches_per_keyword=settings.INSTAGRAM_TARGET_MATCHES_PER_KEYWORD,
        search_batch_size=settings.INSTAGRAM_SEARCH_BATCH_SIZE,
        max_raw_results_per_keyword=settings.INSTAGRAM_MAX_RAW_RESULTS_PER_KEYWORD,
        collect_comments=settings.INSTAGRAM_COLLECT_COMMENTS,
        language_filter=settings.INSTAGRAM_LANGUAGE_FILTER,
    )


PLATFORM_CONFIGS = [
    {
        "name": "TikTok",
        "keywords_path": settings.TIKTOK_KEYWORDS_DOCX_PATH,
        "since": lambda: datetime.now(timezone.utc) - timedelta(hours=settings.TIKTOK_LOOKBACK_HOURS),
        "build_collector": build_tiktok_collector,
        "worksheet_name": "TikTok",
    },
    {
        "name": "Instagram",
        "keywords_path": settings.INSTAGRAM_KEYWORDS_DOCX_PATH,
        "since": lambda: datetime.now(timezone.utc) - timedelta(days=settings.INSTAGRAM_LOOKBACK_DAYS),
        "build_collector": build_instagram_collector,
        "worksheet_name": "Instagram",
    },
]


def main():
    run_started_at = datetime.now(timezone.utc)
    logger.info(f"Log file for this run: logs/{_log_filename}")

    if not settings.APIFY_API_TOKEN:
        logger.error("APIFY_API_TOKEN not configured -- nothing to collect.")
        return 1

    try:
        writer = SheetsWriter(
            service_account_file=settings.GOOGLE_SERVICE_ACCOUNT_FILE,
            sheet_id=settings.GOOGLE_SHEET_ID,
        )
    except Exception as e:
        logger.exception(f"Failed to connect to Google Sheets: {e}")
        return 1

    total_rows_collected = 0
    total_rows_written = 0
    any_platform_failed = False

    for config in PLATFORM_CONFIGS:
        platform_name = config["name"]

        try:
            keywords = extract_keywords(config["keywords_path"])
            logger.info(f"[{platform_name}] Loaded {len(keywords)} keywords: {keywords}")
        except (FileNotFoundError, ValueError) as e:
            logger.error(f"[{platform_name}] Keyword loading failed: {e} -- skipping")
            any_platform_failed = True
            continue

        since = config["since"]()
        logger.info(f"[{platform_name}] Collecting since: {since.isoformat()}")

        collector = config["build_collector"](keywords, since)

        try:
            rows = collector.collect()
        except Exception as e:
            logger.exception(f"[{platform_name}] Collector failed: {e}")
            any_platform_failed = True
            continue

        total_rows_collected += len(rows)
        logger.info(f"[{platform_name}] Collected {len(rows)} rows")

        try:
            written = writer.write_rows(rows, worksheet_name=config["worksheet_name"], collected_at_iso=run_started_at.isoformat())
            total_rows_written += written
        except Exception as e:
            logger.exception(f"[{platform_name}] Google Sheets write failed: {e}")
            any_platform_failed = True

    logger.info(f"Run summary: {total_rows_collected} rows collected, {total_rows_written} new rows written")

    if any_platform_failed:
        logger.warning("One or more platforms had errors this run")

    _write_github_step_summary(total_rows_collected=total_rows_collected, total_rows_written=total_rows_written)
    return 1 if any_platform_failed else 0


def _write_github_step_summary(total_rows_collected, total_rows_written):
    import os
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    lines = [
        "## Keyword monitor run summary",
        f"- **Total rows collected:** {total_rows_collected}",
        f"- **Total new rows written:** {total_rows_written}",
    ]
    with open(summary_path, "a") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    sys.exit(main())
