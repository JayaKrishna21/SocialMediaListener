"""
Instagram collector, via Apify.
"""
import logging
from datetime import datetime, timezone

import requests
from langdetect import detect, LangDetectException

from collectors.base import BaseCollector

logger = logging.getLogger(__name__)

APIFY_BASE_URL = "https://api.apify.com/v2/acts"
APIFY_TIMEOUT_SECONDS = 180


class InstagramCollector(BaseCollector):
    platform_name = "Instagram"

    def __init__(self, keywords, since, apify_token,
                 hashtag_actor_id="apify/instagram-hashtag-scraper",
                 comments_actor_id="apify/instagram-comment-scraper",
                 target_matches_per_keyword=10,
                 search_batch_size=20,
                 max_raw_results_per_keyword=100,
                 max_comments_per_post=30,
                 collect_comments=False,
                 language_filter="en",
                 min_likes=20,
                 known_urls=None):
        super().__init__(keywords, since, known_urls=known_urls)
        self.apify_token = apify_token
        self.hashtag_actor_id = hashtag_actor_id
        self.comments_actor_id = comments_actor_id
        self.target_matches_per_keyword = target_matches_per_keyword
        self.search_batch_size = search_batch_size
        self.max_raw_results_per_keyword = max_raw_results_per_keyword
        self.max_comments_per_post = max_comments_per_post
        self.collect_comments = collect_comments
        self.language_filter = language_filter
        self.min_likes = min_likes

    def collect(self):
        rows = []
        self._seen_urls = set(self.known_urls)
        for keyword in self.keywords:
            if not keyword.startswith("#"):
                logger.info(f"Instagram: skipping '{keyword}' -- hashtag-only")
                continue
            rows.extend(self._collect_for_keyword(keyword))
        logger.info(f"Instagram: collected {len(rows)} rows across {len(self.keywords)} keywords")
        return rows

    def _collect_for_keyword(self, keyword):
        rows = []
        matches_found = 0
        total_requested = 0
        batch_size = self.search_batch_size

        while matches_found < self.target_matches_per_keyword and total_requested < self.max_raw_results_per_keyword:
            remaining_budget = self.max_raw_results_per_keyword - total_requested
            this_batch_size = min(batch_size, remaining_budget)

            try:
                posts = self._search_by_hashtag(keyword, this_batch_size)
            except requests.HTTPError as e:
                status = e.response.status_code if e.response is not None else None
                if status in (401, 403):
                    logger.error(f"Instagram auth failed for '{keyword}' (HTTP {status}) -- check APIFY_API_TOKEN")
                    raise
                logger.warning(f"Instagram hashtag search failed for '{keyword}': {e}")
                break
            except requests.RequestException as e:
                logger.warning(f"Instagram hashtag search failed for '{keyword}': {e}")
                break

            total_requested += this_batch_size

            for post in posts:
                url = post.get("url", "")
                if url in self._seen_urls or not url:
                    continue
                self._seen_urls.add(url)

                post_time = post.get("_parsed_time")
                if post_time is None or post_time < self.since:
                    continue

                if self.language_filter and not self._is_language_match(post.get("text", "")):
                    continue

                if post.get("_likes_count", 0) < self.min_likes:
                    continue

                keyword_lower = keyword.lstrip("#").lower()
                caption_matches = keyword_lower in post.get("text", "").lower()

                if caption_matches:
                    rows.append(self._make_row(
                        timestamp=post_time, author=post.get("author"),
                        row_type="Post", matched_keyword=keyword,
                        content=post.get("text", ""), url=url,
                    ))
                    matches_found += 1

                if self.collect_comments:
                    try:
                        rows.extend(self._collect_matching_comments(url, keyword))
                    except requests.RequestException as e:
                        logger.warning(f"Instagram comment fetch failed for post {url}: {e}")

                if matches_found >= self.target_matches_per_keyword:
                    break

            batch_size *= 2

        if matches_found < self.target_matches_per_keyword:
            logger.info(f"Instagram '{keyword}': only found {matches_found}/{self.target_matches_per_keyword} matches after requesting {total_requested} raw posts (cost cap reached)")
        else:
            logger.info(f"Instagram '{keyword}': found {matches_found} matches from {total_requested} raw posts requested")

        return rows

    def _is_language_match(self, text):
        if not text or not text.strip():
            return True

        meaningful_text = " ".join(
            word for word in text.split() if not word.startswith("#") and not word.startswith("@")
        )

        if len(meaningful_text.strip()) < 20:
            return True

        try:
            detected = detect(meaningful_text)
        except LangDetectException:
            return True

        return detected == self.language_filter

    def _search_by_hashtag(self, hashtag, results_count):
        clean_tag = hashtag.lstrip("#")
        run_input = {
            "hashtags": [clean_tag],
            "keywordSearch": False,
            "resultsLimit": results_count,
            "resultsType": "posts",
        }
        items = self._run_actor(self.hashtag_actor_id, run_input)
        return [self._parse_post_item(item) for item in items]

    def _parse_post_item(self, item):
        author = item.get("ownerUsername")
        url = item.get("url", "")
        text = item.get("caption", "")

        timestamp_raw = item.get("timestamp")
        parsed_time = None
        if timestamp_raw:
            try:
                parsed_time = datetime.fromisoformat(timestamp_raw.replace("Z", "+00:00"))
            except ValueError:
                parsed_time = None

        return {
            "author": author, "url": url, "text": text,
            "_parsed_time": parsed_time,
            "_likes_count": item.get("likesCount", 0),
        }

    def _collect_matching_comments(self, post_url, keyword):
        run_input = {
            "directUrls": [post_url],
            "includeNestedComments": False,
            "resultsLimit": self.max_comments_per_post,
        }
        items = self._run_actor(self.comments_actor_id, run_input)

        keyword_lower = keyword.lstrip("#").lower()
        rows = []

        for item in items:
            comment_text = item.get("text")
            if not comment_text:
                continue
            if keyword_lower not in comment_text.lower():
                continue

            if self.language_filter and not self._is_language_match(comment_text):
                continue

            timestamp_raw = item.get("timestamp")
            comment_time = None
            if timestamp_raw:
                try:
                    comment_time = datetime.fromisoformat(timestamp_raw.replace("Z", "+00:00"))
                except ValueError:
                    comment_time = None

            if comment_time is None or comment_time < self.since:
                continue

            rows.append(self._make_row(
                timestamp=comment_time, author=item.get("ownerUsername"),
                row_type="Comment", matched_keyword=keyword,
                content=comment_text, url=item.get("postUrl", post_url),
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
