"""
TikTok collector, via Apify.
"""
import logging
from datetime import datetime, timezone

import requests

from collectors.base import BaseCollector

logger = logging.getLogger(__name__)

APIFY_BASE_URL = "https://api.apify.com/v2/acts"
APIFY_TIMEOUT_SECONDS = 180


class TikTokCollector(BaseCollector):
    platform_name = "TikTok"

    def __init__(self, keywords, since, apify_token,
                 search_actor_id="clockworks/tiktok-scraper",
                 hashtag_actor_id="clockworks/tiktok-scraper",
                 comments_actor_id="clockworks/tiktok-comments-scraper",
                 target_matches_per_keyword=10,
                 search_batch_size=20,
                 max_raw_results_per_keyword=100,
                 max_comments_per_video=30,
                 language_filter="en",
                 collect_comments=True):
        super().__init__(keywords, since)
        self.apify_token = apify_token
        self.search_actor_id = search_actor_id
        self.hashtag_actor_id = hashtag_actor_id
        self.comments_actor_id = comments_actor_id
        self.target_matches_per_keyword = target_matches_per_keyword
        self.search_batch_size = search_batch_size
        self.max_raw_results_per_keyword = max_raw_results_per_keyword
        self.max_comments_per_video = max_comments_per_video
        self.language_filter = language_filter
        self.collect_comments = collect_comments

    def collect(self):
        rows = []
        for keyword in self.keywords:
            rows.extend(self._collect_for_keyword(keyword))
        logger.info(f"TikTok: collected {len(rows)} rows across {len(self.keywords)} keywords")
        return rows

    def _collect_for_keyword(self, keyword):
        rows = []
        matches_found = 0
        total_requested = 0
        batch_size = self.search_batch_size
        seen_urls = set()

        while matches_found < self.target_matches_per_keyword and total_requested < self.max_raw_results_per_keyword:
            remaining_budget = self.max_raw_results_per_keyword - total_requested
            this_batch_size = min(batch_size, remaining_budget)

            try:
                if keyword.startswith("#"):
                    videos = self._search_by_hashtag(keyword, this_batch_size)
                else:
                    videos = self._search_by_keyword(keyword, this_batch_size)
            except requests.RequestException as e:
                logger.warning(f"TikTok search failed for keyword '{keyword}': {e}")
                break

            total_requested += this_batch_size

            for video in videos:
                url = video.get("url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                video_time = video.get("_parsed_time")
                if video_time is None or video_time < self.since:
                    continue

                if self.language_filter and video.get("_language") != self.language_filter:
                    continue

                keyword_lower = keyword.lstrip("#").lower()
                caption_matches = keyword_lower in video.get("text", "").lower()

                if caption_matches:
                    rows.append(self._make_row(
                        timestamp=video_time, author=video.get("author"),
                        row_type="Post", matched_keyword=keyword,
                        content=video.get("text", ""), url=url,
                    ))
                    matches_found += 1

                if self.collect_comments:
                    try:
                        rows.extend(self._collect_matching_comments(video, keyword))
                    except requests.RequestException as e:
                        logger.warning(f"TikTok comment fetch failed for video {url}: {e}")

                if matches_found >= self.target_matches_per_keyword:
                    break

            batch_size *= 2

        if matches_found < self.target_matches_per_keyword:
            logger.info(f"TikTok '{keyword}': only found {matches_found}/{self.target_matches_per_keyword} matches after requesting {total_requested} raw results (cost cap reached)")
        else:
            logger.info(f"TikTok '{keyword}': found {matches_found} matches from {total_requested} raw results requested")

        return rows

    def _search_by_keyword(self, keyword, results_count):
        run_input = {
            "searchQueries": [keyword], "resultsPerPage": results_count,
            "shouldDownloadVideos": False, "shouldDownloadCovers": False,
        }
        items = self._run_actor(self.search_actor_id, run_input)
        return [self._parse_video_item(item) for item in items]

    def _search_by_hashtag(self, hashtag, results_count):
        clean_tag = hashtag.lstrip("#")
        run_input = {
            "hashtags": [clean_tag], "resultsPerPage": results_count,
            "shouldDownloadVideos": False, "shouldDownloadCovers": False,
        }
        items = self._run_actor(self.hashtag_actor_id, run_input)
        return [self._parse_video_item(item) for item in items]

    def _parse_video_item(self, item):
        author = (item.get("authorMeta") or {}).get("name") or item.get("author")
        url = item.get("webVideoUrl") or item.get("url", "")
        text = item.get("text") or item.get("desc", "")

        create_time = item.get("createTimeISO")
        parsed_time = None
        if create_time:
            try:
                parsed_time = datetime.fromisoformat(create_time.replace("Z", "+00:00"))
            except ValueError:
                parsed_time = None
        elif item.get("createTime"):
            try:
                parsed_time = datetime.fromtimestamp(int(item["createTime"]), tz=timezone.utc)
            except (ValueError, TypeError):
                parsed_time = None

        return {
            "author": author, "url": url, "text": text,
            "_parsed_time": parsed_time, "_language": item.get("textLanguage"),
        }

    def _collect_matching_comments(self, video, keyword):
        video_url = video.get("url")
        if not video_url:
            return []

        run_input = {"postURLs": [video_url], "commentsPerPost": self.max_comments_per_video}
        items = self._run_actor(self.comments_actor_id, run_input)

        keyword_lower = keyword.lstrip("#").lower()
        rows = []

        for item in items:
            comment_text = item.get("text", "")
            if keyword_lower not in comment_text.lower():
                continue

            create_time = item.get("createTimeISO")
            comment_time = None
            if create_time:
                try:
                    comment_time = datetime.fromisoformat(create_time.replace("Z", "+00:00"))
                except ValueError:
                    comment_time = None
            elif item.get("createTime"):
                try:
                    comment_time = datetime.fromtimestamp(int(item["createTime"]), tz=timezone.utc)
                except (ValueError, TypeError):
                    comment_time = None

            if comment_time is None or comment_time < self.since:
                continue

            rows.append(self._make_row(
                timestamp=comment_time, author=item.get("uniqueId") or item.get("username"),
                row_type="Comment", matched_keyword=keyword,
                content=comment_text, url=video_url,
            ))

        return rows

    def _run_actor(self, actor_id, run_input):
        url_safe_actor_id = actor_id.replace("/", "~")
        url = f"{APIFY_BASE_URL}/{url_safe_actor_id}/run-sync-get-dataset-items"
        response = requests.post(
            url, params={"token": self.apify_token}, json=run_input,
            timeout=APIFY_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()
