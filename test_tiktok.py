import sys
sys.path.insert(0, "src")

from datetime import datetime, timezone, timedelta
from collectors.tiktok_collector import TikTokCollector


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_tiktok.py YOUR_APIFY_TOKEN")
        sys.exit(1)

    token = sys.argv[1]

    print("Running TikTok test search (this may take up to a couple minutes)...")

    collector = TikTokCollector(
        keywords=["#cookies"],
        since=datetime.now(timezone.utc) - timedelta(days=7),
        apify_token=token,
        target_matches_per_keyword=5,
        search_batch_size=20,
        max_raw_results_per_keyword=100,
        collect_comments=False,
    )

    try:
        rows = collector.collect()
    except Exception as error:
        print("FAILED: " + str(error))
        sys.exit(1)

    print("Got " + str(len(rows)) + " rows")
    print("")

    for row in rows:
        row_type = row["type"]
        author = str(row["author"])
        snippet = row["content_snippet"]
        print("  [" + row_type + "] " + author + ": " + snippet)

    if len(rows) == 0:
        print("No matches found -- this hashtag may have very little")
        print("content, or try widening the time window further.")


if __name__ == "__main__":
    main()
