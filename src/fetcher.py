"""
Fetcher Module for Daily GenAI News Aggregator.

Scrapes, parses, filters, and deduplicates news and research items from authoritative sources.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import logging
import re
from typing import List, Dict, Optional, Set
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode

import bs4
import feedparser
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("Fetcher")


@dataclass
class NewsItem:
    title: str
    url: str
    source: str
    published_at: datetime
    raw_summary: str = ""
    authors: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "published_at": self.published_at.isoformat(),
            "raw_summary": self.raw_summary,
            "authors": self.authors,
            "tags": self.tags,
        }


class NewsFetcher:
    """Fetches and deduplicates GenAI news from RSS feeds and APIs."""

    RSS_SOURCES = [
        # Research highlights
        {
            "name": "ArXiv cs.AI",
            "url": "http://export.arxiv.org/rss/cs.AI",
            "category": "Research",
        },
        {
            "name": "ArXiv cs.CL (NLP)",
            "url": "http://export.arxiv.org/rss/cs.CL",
            "category": "Research",
        },
        {
            "name": "Hugging Face Blog",
            "url": "https://huggingface.co/blog/feed.xml",
            "category": "Open Source",
        },
        # Tech & AI News
        {
            "name": "TechCrunch AI",
            "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
            "category": "Industry",
        },
        {
            "name": "VentureBeat AI",
            "url": "https://venturebeat.com/category/ai/feed/",
            "category": "Industry",
        },
        {
            "name": "MIT Technology Review AI",
            "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed/",
            "category": "Industry",
        },
        # Major Lab Blogs
        {
            "name": "OpenAI News",
            "url": "https://openai.com/news/rss.xml",
            "category": "Lab Release",
        },
        {
            "name": "Google DeepMind Blog",
            "url": "https://deepmind.google/blog/rss.xml",
            "category": "Lab Release",
        },
    ]

    USER_AGENT = "DailyGenAINewsAggregator/1.0 (+https://github.com/daily-genai-briefing)"

    def __init__(self, hours_lookback: int = 24):
        self.hours_lookback = hours_lookback
        self.cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_lookback)

    def clean_url(self, url: str) -> str:
        """Removes tracking query parameters (utm_*, etc.) and normalizes URLs."""
        if not url:
            return ""
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        # Filter out common tracking parameters
        clean_query = {k: v for k, v in query.items() if not k.startswith("utm_") and k not in ["ref", "source", "fbclid"]}
        new_query_str = urlencode(clean_query, doseq=True)
        clean_parsed = parsed._replace(query=new_query_str, fragment="")
        # Remove trailing slash from path
        path = clean_parsed.path.rstrip("/")
        clean_parsed = clean_parsed._replace(path=path)
        return urlunparse(clean_parsed)

    def clean_text(self, html_or_text: str) -> str:
        """Strips HTML tags and normalizes whitespace."""
        if not html_or_text:
            return ""
        soup = bs4.BeautifulSoup(html_or_text, "html.parser")
        text = soup.get_text(separator=" ")
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def parse_entry_date(self, entry) -> Optional[datetime]:
        """Extracts publication date from an RSS feed entry, defaulting to current time if absent."""
        parsed_dt = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                parsed_dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            except Exception:
                pass
        elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
            try:
                parsed_dt = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
            except Exception:
                pass

        if not parsed_dt:
            # Fallback to now if date cannot be determined
            parsed_dt = datetime.now(timezone.utc)

        return parsed_dt

    def fetch_rss_sources(self) -> List[NewsItem]:
        """Fetches stories from configured RSS feeds within the lookback window."""
        items: List[NewsItem] = []
        session = requests.Session()
        session.headers.update({"User-Agent": self.USER_AGENT})

        for source in self.RSS_SOURCES:
            logger.info(f"Fetching RSS feed: {source['name']} ({source['url']})")
            try:
                resp = session.get(source["url"], timeout=10)
                if resp.status_code != 200:
                    logger.warning(f"HTTP {resp.status_code} when fetching {source['name']}")
                    continue

                feed = feedparser.parse(resp.content)
                for entry in feed.entries:
                    pub_date = self.parse_entry_date(entry)

                    # Date filter: keep items within lookback window
                    if pub_date < self.cutoff_time:
                        continue

                    title = self.clean_text(getattr(entry, "title", ""))
                    link = self.clean_url(getattr(entry, "link", ""))
                    summary = self.clean_text(getattr(entry, "summary", "") or getattr(entry, "description", ""))

                    if not title or not link:
                        continue

                    authors = []
                    if hasattr(entry, "author") and entry.author:
                        authors.append(entry.author)

                    items.append(
                        NewsItem(
                            title=title,
                            url=link,
                            source=source["name"],
                            published_at=pub_date,
                            raw_summary=summary[:800],
                            authors=authors,
                            tags=[source["category"]],
                        )
                    )
            except Exception as e:
                logger.error(f"Error fetching {source['name']}: {e}")

        logger.info(f"Fetched {len(items)} raw RSS items.")
        return items

    def fetch_hacker_news_ai(self, max_items: int = 25) -> List[NewsItem]:
        """Fetches top AI stories from Hacker News via the Algolia API."""
        logger.info("Fetching Hacker News AI stories via Algolia Search API...")
        items: List[NewsItem] = []
        url = "https://hn.algolia.com/api/v1/search_by_date"
        params = {
            "tags": "story",
            "query": "LLM OR GPT OR Claude OR Gemini OR Transformer OR Diffusion OR GenAI OR OpenAI OR Anthropic",
            "numericFilters": f"created_at_i>{int(self.cutoff_time.timestamp())}",
            "hitsPerPage": max_items,
        }
        try:
            resp = requests.get(url, params=params, headers={"User-Agent": self.USER_AGENT}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for hit in data.get("hits", []):
                    title = hit.get("title", "")
                    story_url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
                    created_at_i = hit.get("created_at_i")
                    pub_date = datetime.fromtimestamp(created_at_i, tz=timezone.utc) if created_at_i else datetime.now(timezone.utc)
                    points = hit.get("points", 0)

                    # Filter for stories with minimal community interest (> 15 points or high relevance)
                    if points < 10 and not any(kw in title.lower() for kw in ["openai", "anthropic", "google", "meta", "arxiv", "release"]):
                        continue

                    items.append(
                        NewsItem(
                            title=title,
                            url=self.clean_url(story_url),
                            source="Hacker News AI",
                            published_at=pub_date,
                            raw_summary=f"Hacker News discussion ({points} points, {hit.get('num_comments', 0)} comments).",
                            tags=["Discussion", "Community"],
                        )
                    )
        except Exception as e:
            logger.error(f"Error fetching Hacker News AI items: {e}")

        logger.info(f"Fetched {len(items)} items from Hacker News.")
        return items

    def _token_set(self, text: str) -> Set[str]:
        """Extracts normalized alphanumeric words from text."""
        words = re.findall(r"\w+", text.lower())
        stopwords = {"a", "an", "the", "and", "or", "in", "of", "to", "for", "with", "on", "at", "by", "from", "is", "are", "new", "ai", "using", "model", "models"}
        return {w for w in words if len(w) > 2 and w not in stopwords}

    def jaccard_similarity(self, set1: Set[str], set2: Set[str]) -> float:
        """Calculates Jaccard similarity index between two word sets."""
        if not set1 or not set2:
            return 0.0
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        return intersection / float(union)

    def deduplicate(self, items: List[NewsItem], similarity_threshold: float = 0.55) -> List[NewsItem]:
        """
        Deduplicates news items based on:
        1. Exact/Normalized URL matching
        2. Title Jaccard similarity matching
        """
        deduped: List[NewsItem] = []
        seen_urls: Set[str] = set()

        for item in items:
            clean_link = item.url
            if clean_link in seen_urls:
                continue

            # Check semantic/title similarity with existing deduped items
            item_tokens = self._token_set(item.title)
            is_duplicate = False

            for existing in deduped:
                existing_tokens = self._token_set(existing.title)
                sim = self.jaccard_similarity(item_tokens, existing_tokens)
                if sim >= similarity_threshold:
                    is_duplicate = True
                    logger.debug(f"Duplicate detected: '{item.title}' matches '{existing.title}' (similarity={sim:.2f})")
                    # If current item is from a primary lab or paper source, prefer it as the main title/url
                    if ("OpenAI" in item.source or "Anthropic" in item.source or "ArXiv" in item.source) and not ("OpenAI" in existing.source or "ArXiv" in existing.source):
                        existing.title = item.title
                        existing.url = item.url
                        existing.source = f"{item.source} (via {existing.source})"
                    break

            if not is_duplicate:
                seen_urls.add(clean_link)
                deduped.append(item)

        logger.info(f"Deduplicated {len(items)} items down to {len(deduped)} items.")
        return deduped

    def fetch_all(self) -> List[NewsItem]:
        """Executes full fetch, combine, and deduplication pipeline."""
        raw_items = []
        raw_items.extend(self.fetch_rss_sources())
        raw_items.extend(self.fetch_hacker_news_ai())

        # Sort items by date descending
        raw_items.sort(key=lambda x: x.published_at, reverse=True)

        final_items = self.deduplicate(raw_items)
        return final_items


if __name__ == "__main__":
    fetcher = NewsFetcher(hours_lookback=48)
    results = fetcher.fetch_all()
    print(f"Total deduplicated items fetched: {len(results)}")
    for i, res in enumerate(results[:10], 1):
        print(f"{i}. [{res.source}] [{', '.join(res.tags)}] {res.title}")
        print(f"   URL: {res.url}")
        print(f"   Date: {res.published_at}")
        print("-" * 60)
