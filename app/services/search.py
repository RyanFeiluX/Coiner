import logging
from typing import Dict, List, Optional

from loguru import logger

from app.config import config

logger = logging.getLogger(__name__)

_TAVILY_AVAILABLE = False
try:
    from tavily import TavilyClient
    _TAVILY_AVAILABLE = True
except ImportError:
    logger.warning("tavily-python not installed. Web search disabled. Run: pip install tavily-python")


def _get_tavily_client():
    api_key = config.app.get("tavily_api_key", "") or config.tavily.get("api_key", "")
    if not api_key:
        return None
    try:
        return TavilyClient(api_key=api_key)
    except Exception as e:
        logger.error(f"Failed to create TavilyClient: {e}")
        return None


def search_web(query: str, num_results: int = 5, source_preference: str = "balanced") -> List[Dict]:
    if not _TAVILY_AVAILABLE:
        logger.warning("tavily-python not installed, cannot search web")
        return []

    client = _get_tavily_client()
    if not client:
        logger.warning("Tavily API key not configured, skipping web search")
        return []

    try:
        topic = "general"
        if source_preference == "latest":
            topic = "news"
        elif source_preference == "authoritative":
            topic = "general"

        response = client.search(
            query=query,
            search_depth="advanced" if num_results > 5 else "basic",
            max_results=min(num_results, 20),
            topic=topic,
            include_answer=True,
            include_raw_content=False,
        )

        results = response.get("results", [])
        logger.info(f"Tavily search for '{query}' returned {len(results)} results (topic={topic})")
        return results
    except Exception as e:
        logger.error(f"Tavily search failed for query '{query}': {e}")
        return []


def _build_search_queries(topic: str, expansion_depth: str, search_round: int = 0) -> List[str]:
    if search_round == 0:
        return [topic]

    if expansion_depth == "topic_only":
        return [topic]

    if expansion_depth == "moderate":
        return [
            f"{topic} 最新进展",
            f"{topic} 详细介绍",
        ]

    return [
        f"{topic} 最新进展 2025 2026",
        f"{topic} 详细介绍 分析",
        f"{topic} 案例 数据 统计",
        f"{topic} 未来趋势 前景",
    ]


def search_and_summarize(
    topic: str,
    rounds: int = 1,
    num_results: int = 5,
    source_preference: str = "balanced",
    expansion_depth: str = "moderate",
) -> str:
    if rounds < 1:
        rounds = 1
    if num_results < 1:
        num_results = 1

    all_results = []
    seen_urls = set()

    for round_idx in range(rounds):
        queries = _build_search_queries(topic, expansion_depth, round_idx)
        logger.info(f"Search round {round_idx + 1}/{rounds}: queries={queries}")

        for query in queries:
            results = search_web(query, num_results=num_results, source_preference=source_preference)
            for r in results:
                url = r.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(r)

    if not all_results:
        logger.info(f"No search results found for topic '{topic}'")
        return ""

    lines = []
    for i, r in enumerate(all_results[:num_results * max(rounds, 1)]):
        title = r.get("title", "").strip()
        content = r.get("content", "").strip()
        url = r.get("url", "").strip()
        if title or content:
            lines.append(f"[{i + 1}] {title}")
            if content:
                snippet = content[:500]
                lines.append(f"    {snippet}")
            if url:
                lines.append(f"    Source: {url}")

    summary = "\n".join(lines)
    logger.info(f"Search summary for '{topic}': {len(all_results)} unique results, {len(summary)} chars")
    return summary
