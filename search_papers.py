"""Search arXiv and Google Scholar, then merge results."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime

from search_arxiv import search_arxiv
from search_scholar import search_scholar


def _normalize_title(title: str | None) -> str:
    if not title:
        return ""
    normalized = title.lower()
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _merge_papers(arxiv_papers: list[dict], scholar_papers: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}

    for paper in arxiv_papers:
        key = _normalize_title(paper.get("title"))
        if not key:
            continue
        merged[key] = {**paper, "sources": ["arxiv"]}

    for paper in scholar_papers:
        key = _normalize_title(paper.get("title"))
        if not key:
            continue
        if key in merged:
            existing = merged[key]
            existing["sources"] = sorted(set(existing.get("sources", []) + ["google_scholar"]))
            existing["citations"] = paper.get("citations")
            if not existing.get("venue") and paper.get("venue"):
                existing["venue"] = paper.get("venue")
            if not existing.get("url"):
                existing["url"] = paper.get("url")
            if not existing.get("summary") and paper.get("summary"):
                existing["summary"] = paper.get("summary")
        else:
            merged[key] = {**paper, "sources": ["google_scholar"]}

    for paper in merged.values():
        paper["source"] = " / ".join(paper.pop("sources", []))

    return list(merged.values())


def _rank_for_pickup(papers: list[dict], limit: int = 5) -> list[dict]:
    def sort_key(paper: dict) -> tuple:
        citations = paper.get("citations")
        citation_score = citations if isinstance(citations, int) else -1
        published = paper.get("published") or "0000"
        return (citation_score, published)

    ranked = sorted(papers, key=sort_key, reverse=True)
    return ranked[:limit]


def search_papers(query: str, max_results: int = 20) -> dict:
    arxiv_papers = search_arxiv(query, max_results=max_results)
    scholar_papers = search_scholar(query, max_results=max_results)
    merged = _merge_papers(arxiv_papers, scholar_papers)
    suggested = _rank_for_pickup(merged, limit=5)
    return {
        "query": query,
        "searched_at": datetime.now().isoformat(timespec="seconds"),
        "arxiv_count": len(arxiv_papers),
        "scholar_count": len(scholar_papers),
        "merged_count": len(merged),
        "suggested_pickups": suggested,
        "all_results": merged,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search arXiv and Google Scholar, merge and suggest top papers."
    )
    parser.add_argument("query", help="Search keywords")
    parser.add_argument(
        "--max-results",
        type=int,
        default=20,
        help="Maximum results per source (default: 20)",
    )
    args = parser.parse_args()

    result = search_papers(args.query, max_results=args.max_results)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
