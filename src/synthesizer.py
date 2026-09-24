"""
Synthesizer Module for Daily GenAI News Aggregator.

Uses LLM (Google Gemini API / OpenAI API) or rule-based fallback to filter, rank, and summarize top AI news into an executive briefing structure.
"""

from dataclasses import dataclass, field
import json
import logging
import os
from typing import List, Dict, Optional, Any

try:
    from src.fetcher import NewsItem
except ImportError:
    from fetcher import NewsItem

logger = logging.getLogger("Synthesizer")


@dataclass
class StoryBrief:
    headline: str
    url: str
    source: str
    tag: str  # Research, Product, Open Source, Industry
    summary: str  # 2-3 sentence non-fluff explanation of what launched & why it matters
    original_title: str = ""


@dataclass
class DailyDigestContent:
    date_str: str
    macro_overview: str  # 2-sentence top-level overview of macro trends
    top_breakthroughs: List[StoryBrief] = field(default_factory=list)
    notable_releases: List[StoryBrief] = field(default_factory=list)
    total_sources_scanned: int = 0
    total_items_ingested: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date_str": self.date_str,
            "macro_overview": self.macro_overview,
            "top_breakthroughs": [b.__dict__ for b in self.top_breakthroughs],
            "notable_releases": [r.__dict__ for r in self.notable_releases],
            "total_sources_scanned": self.total_sources_scanned,
            "total_items_ingested": self.total_items_ingested,
        }


class NewsSynthesizer:
    """Ranks, filters, and generates concise AI summaries using GenAI APIs."""

    def __init__(self, max_stories: int = 8):
        self.max_stories = max_stories
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")

    def synthesize(self, items: List[NewsItem], date_str: str) -> DailyDigestContent:
        """Processes raw news items and returns a formatted DailyDigestContent."""
        if not items:
            return DailyDigestContent(
                date_str=date_str,
                macro_overview="No major GenAI developments detected in the last 24-hour ingestion window.",
                top_breakthroughs=[],
                notable_releases=[],
                total_sources_scanned=0,
                total_items_ingested=0,
            )

        # Attempt Gemini API
        if self.gemini_key and self.gemini_key.strip() and self.gemini_key != "your_gemini_api_key_here":
            try:
                return self._synthesize_with_gemini(items, date_str)
            except Exception as e:
                logger.error(f"Gemini API synthesis failed ({e}). Falling back to OpenAI or rule-based engine.")

        # Attempt OpenAI API
        if self.openai_key and self.openai_key.strip() and self.openai_key != "your_openai_api_key_here":
            try:
                return self._synthesize_with_openai(items, date_str)
            except Exception as e:
                logger.error(f"OpenAI API synthesis failed ({e}). Falling back to rule-based engine.")

        # Fallback synthesizer
        logger.info("Using Rule-based Fallback Synthesizer (No valid API key provided or API unavailable).")
        return self._synthesize_fallback(items, date_str)

    def _synthesize_with_gemini(self, items: List[NewsItem], date_str: str) -> DailyDigestContent:
        """Synthesizes news using google-genai SDK."""
        from google import genai
        from google.genai import types

        logger.info("Synthesizing briefing via Google Gemini API...")
        client = genai.Client(api_key=self.gemini_key)

        # Select top candidates to send to LLM context window (up to top 30 items)
        candidate_items = items[:30]
        items_payload = []
        for i, item in enumerate(candidate_items, 1):
            items_payload.append({
                "id": i,
                "title": item.title,
                "source": item.source,
                "url": item.url,
                "tag_hint": item.tags[0] if item.tags else "General",
                "snippet": item.raw_summary[:350],
            })

        prompt = f"""You are an executive AI briefing analyst for technical leaders.
Analyze the following list of recent GenAI developments from the last 24 hours.

Select the {self.max_stories} most significant stories.
Generate a JSON object strictly following this structure:

{{
  "macro_overview": "A concise 2-sentence executive summary highlighting today's macro themes, major lab moves, or key technical shifts.",
  "top_breakthroughs": [
    {{
      "id": item_id_number,
      "headline": "Clean executive headline (active voice)",
      "url": "original_url",
      "source": "source_name",
      "tag": "One of: Research, Product, Open Source, Industry",
      "summary": "2-3 sentence non-fluff explanation of what launched and why it matters technically and strategically."
    }}
  ],
  "notable_releases": [
    {{
      "id": item_id_number,
      "headline": "Clean release headline",
      "url": "original_url",
      "source": "source_name",
      "tag": "Open Source or Product",
      "summary": "1-2 sentence quick summary of model/code release."
    }}
  ]
}}

Raw News Items Data:
{json.dumps(items_payload, indent=2)}
"""

        # Try reliable Gemini models
        response = None
        for model_name in ["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-flash-latest"]:
            try:
                logger.info(f"Sending prompt to Gemini model: {model_name}")
                resp = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.2,
                    )
                )
                if resp and resp.text:
                    response = resp
                    break
            except Exception as e:
                logger.warning(f"Gemini model {model_name} failed: {e}. Trying next model...")
                continue

        if not response or not response.text:
            raise RuntimeError("All Gemini model generation attempts failed.")

        raw_json = response.text
        data = json.loads(raw_json)

        top_breakthroughs = []
        for b in data.get("top_breakthroughs", []):
            top_breakthroughs.append(
                StoryBrief(
                    headline=b.get("headline", ""),
                    url=b.get("url", ""),
                    source=b.get("source", ""),
                    tag=b.get("tag", "Industry"),
                    summary=b.get("summary", ""),
                )
            )

        notable_releases = []
        for r in data.get("notable_releases", []):
            notable_releases.append(
                StoryBrief(
                    headline=r.get("headline", ""),
                    url=r.get("url", ""),
                    source=r.get("source", ""),
                    tag=r.get("tag", "Open Source"),
                    summary=r.get("summary", ""),
                )
            )

        return DailyDigestContent(
            date_str=date_str,
            macro_overview=data.get("macro_overview", ""),
            top_breakthroughs=top_breakthroughs,
            notable_releases=notable_releases,
            total_sources_scanned=len(set(item.source for item in items)),
            total_items_ingested=len(items),
        )

    def _synthesize_with_openai(self, items: List[NewsItem], date_str: str) -> DailyDigestContent:
        """Synthesizes news using OpenAI API."""
        import requests

        logger.info("Synthesizing briefing via OpenAI API...")
        candidate_items = items[:30]
        items_payload = [
            {
                "id": i,
                "title": item.title,
                "source": item.source,
                "url": item.url,
                "snippet": item.raw_summary[:350],
            }
            for i, item in enumerate(candidate_items, 1)
        ]

        system_prompt = "You are an AI news analyst. Respond strictly in JSON."
        user_prompt = f"""Select the {self.max_stories} top stories and summarize them into a JSON format with keys:
- macro_overview (2-sentence string)
- top_breakthroughs (array of objects with headline, url, source, tag, summary)
- notable_releases (array of objects with headline, url, source, tag, summary)

Raw Items:
{json.dumps(items_payload)}
"""
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.openai_key}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "content", "content": user_prompt},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.2,
            },
            timeout=30,
        )

        data = resp.json()["choices"][0]["message"]["content"]
        parsed = json.loads(data)

        return DailyDigestContent(
            date_str=date_str,
            macro_overview=parsed.get("macro_overview", ""),
            top_breakthroughs=[StoryBrief(**b) for b in parsed.get("top_breakthroughs", [])],
            notable_releases=[StoryBrief(**r) for r in parsed.get("notable_releases", [])],
            total_sources_scanned=len(set(item.source for item in items)),
            total_items_ingested=len(items),
        )

    def _synthesize_fallback(self, items: List[NewsItem], date_str: str) -> DailyDigestContent:
        """Rule-based fallback engine when no LLM API key is present."""
        # Prioritize lab releases, Hugging Face, Tech stories, then ArXiv research papers
        lab_items = [item for item in items if "OpenAI" in item.source or "DeepMind" in item.source or "Hugging" in item.source]
        tech_items = [item for item in items if "TechCrunch" in item.source or "Hacker News" in item.source or "Technology Review" in item.source]
        research_items = [item for item in items if "ArXiv" in item.source]

        selected: List[NewsItem] = (lab_items + tech_items + research_items)[: self.max_stories]
        if not selected and items:
            selected = items[: self.max_stories]

        top_breakthroughs: List[StoryBrief] = []
        for item in selected:
            # Assign tag
            tag = "Research"
            if "ArXiv" in item.source:
                tag = "Research"
            elif "Hugging" in item.source or "Open Source" in item.tags:
                tag = "Open Source"
            elif "TechCrunch" in item.source or "Technology Review" in item.source:
                tag = "Industry"
            elif "OpenAI" in item.source or "DeepMind" in item.source:
                tag = "Product"

            # Create non-fluff fallback summary
            clean_summary = item.raw_summary.strip()
            if len(clean_summary) > 200:
                clean_summary = clean_summary[:197] + "..."
            if not clean_summary:
                clean_summary = f"New update released via {item.source} regarding {item.title}."

            summary = f"Breakthrough update published in {item.source}. {clean_summary}"

            top_breakthroughs.append(
                StoryBrief(
                    headline=item.title,
                    url=item.url,
                    source=item.source,
                    tag=tag,
                    summary=summary,
                    original_title=item.title,
                )
            )

        sources = set(item.source for item in items)
        macro = (
            f"Today's briefing features {len(top_breakthroughs)} major updates across {len(sources)} sources, "
            f"covering key research papers, open-source model advancements, and industry news."
        )

        return DailyDigestContent(
            date_str=date_str,
            macro_overview=macro,
            top_breakthroughs=top_breakthroughs,
            notable_releases=[],
            total_sources_scanned=len(sources),
            total_items_ingested=len(items),
        )


if __name__ == "__main__":
    try:
        from src.fetcher import NewsFetcher
    except ImportError:
        from fetcher import NewsFetcher
    from datetime import datetime

    fetcher = NewsFetcher(hours_lookback=48)
    items = fetcher.fetch_all()

    synthesizer = NewsSynthesizer(max_stories=5)
    today = datetime.now().strftime("%B %d, %Y")
    digest = synthesizer.synthesize(items, today)

    print("\n=== SYNTHESIZED DIGEST PREVIEW ===")
    print(f"Date: {digest.date_str}")
    print(f"Macro Overview: {digest.macro_overview}\n")
    for b in digest.top_breakthroughs:
        print(f"[{b.tag}] {b.headline}")
        print(f"Source: {b.source} | URL: {b.url}")
        print(f"Summary: {b.summary}\n")
