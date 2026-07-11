"""Fetch Connected Papers graph data and related papers sorted by citations."""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1"
USER_AGENT = "PaperAgent/1.0 (research project)"


def _request_json(url: str, retries: int = 3) -> dict | list | None:
    for attempt in range(retries):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as error:
            if error.code == 429 and attempt + 1 < retries:
                time.sleep(2 ** attempt)
                continue
            return None
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
            return None
    return None


def _extract_arxiv_id(value: str) -> str | None:
    match = re.search(r"(\d{4}\.\d{4,5}(?:v\d+)?)", value)
    return match.group(1) if match else None


def _extract_doi(value: str) -> str | None:
    match = re.search(r"(10\.\d{4,9}/\S+)", value)
    return match.group(1).rstrip(").,") if match else None


def resolve_paper(query: str) -> dict | None:
    """Resolve a paper query to Semantic Scholar metadata."""
    fields = "paperId,title,authors,year,citationCount,externalIds,url,abstract,venue,publicationVenue,journal"
    arxiv_id = _extract_arxiv_id(query)
    if arxiv_id:
        data = _request_json(f"{SEMANTIC_SCHOLAR_API}/paper/arXiv:{arxiv_id}?fields={fields}")
        if isinstance(data, dict) and data.get("paperId"):
            return data

    doi = _extract_doi(query)
    if doi:
        encoded_doi = urllib.parse.quote(doi, safe="")
        data = _request_json(f"{SEMANTIC_SCHOLAR_API}/paper/DOI:{encoded_doi}?fields={fields}")
        if isinstance(data, dict) and data.get("paperId"):
            return data

    encoded_query = urllib.parse.quote(query)
    search = _request_json(
        f"{SEMANTIC_SCHOLAR_API}/paper/search?query={encoded_query}&limit=1&fields={fields}"
    )
    if isinstance(search, dict):
        items = search.get("data") or []
        if items:
            return items[0]
    return None


def connected_papers_url(title: str | None, paper_id: str | None = None) -> str:
    if paper_id:
        return f"https://www.connectedpapers.com/main/{paper_id}/graph"
    encoded = urllib.parse.quote(title or "")
    return f"https://www.connectedpapers.com/search?q={encoded}"


def _extract_venue_from_paper(paper: dict | Any) -> str | None:
    if isinstance(paper, dict):
        venue = paper.get("venue")
        if isinstance(venue, str) and venue.strip():
            return venue.strip()
        publication_venue = paper.get("publicationVenue")
        if isinstance(publication_venue, dict):
            name = publication_venue.get("name")
            if name:
                return name
        journal = paper.get("journal")
        if isinstance(journal, dict):
            name = journal.get("name")
            if name:
                return name
        journal_name = getattr(paper, "journalName", None)
        if journal_name:
            return journal_name
        venue_name = getattr(paper, "venue", None)
        if venue_name:
            return venue_name
    else:
        journal_name = getattr(paper, "journalName", None)
        if journal_name:
            return journal_name
        venue_name = getattr(paper, "venue", None)
        if venue_name:
            return venue_name
    return None


def _paper_summary(paper: Any, citations: int | None = None) -> dict:
    authors = []
    raw_authors = getattr(paper, "authors", None) or paper.get("authors", [])
    for author in raw_authors:
        if isinstance(author, dict):
            authors.append(author.get("name"))
        else:
            authors.append(getattr(author, "name", None))

    if isinstance(paper, dict):
        return {
            "title": paper.get("title"),
            "authors": [name for name in authors if name],
            "year": paper.get("year"),
            "citations": citations if citations is not None else paper.get("citationCount"),
            "url": paper.get("url"),
            "paper_id": paper.get("paperId") or paper.get("id") or paper.get("paper_id"),
            "venue": _extract_venue_from_paper(paper),
        }

    return {
        "title": getattr(paper, "title", None),
        "authors": [name for name in authors if name],
        "year": getattr(paper, "year", None),
        "citations": citations,
        "url": getattr(paper, "url", None),
        "paper_id": getattr(paper, "paperId", None) or getattr(paper, "id", None),
        "venue": _extract_venue_from_paper(paper),
    }


def _fetch_citation_counts(paper_ids: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for index in range(0, len(paper_ids), 500):
        batch = paper_ids[index : index + 500]
        payload = json.dumps({"ids": batch}).encode()
        request = urllib.request.Request(
            f"{SEMANTIC_SCHOLAR_API}/paper/batch?fields=paperId,citationCount",
            data=payload,
            headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                papers = json.loads(response.read().decode())
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
            continue
        if not isinstance(papers, list):
            continue
        for paper in papers:
            if paper and paper.get("paperId") is not None:
                counts[paper["paperId"]] = paper.get("citationCount", 0)
    return counts


def _collect_related_from_graph(graph: Any, origin_id: str) -> list[dict]:
    related: dict[str, dict] = {}

    for paper in graph.nodes.values():
        paper_id = getattr(paper, "paperId", None) or getattr(paper, "id", None)
        if not paper_id or paper_id == origin_id:
            continue
        related[paper_id] = _paper_summary(paper)

    for paper in graph.common_citations:
        paper_id = getattr(paper, "paperId", None) or getattr(paper, "paper_id", None)
        if not paper_id or paper_id == origin_id:
            continue
        related[paper_id] = _paper_summary(paper)

    missing_ids = [paper_id for paper_id, item in related.items() if item.get("citations") is None]
    if missing_ids:
        counts = _fetch_citation_counts(missing_ids)
        for paper_id, count in counts.items():
            if paper_id in related:
                related[paper_id]["citations"] = count

    ranked = sorted(
        related.values(),
        key=lambda item: (item.get("citations") if isinstance(item.get("citations"), int) else -1, item.get("year") or 0),
        reverse=True,
    )
    return ranked


def _fetch_semantic_scholar_citations(origin_id: str, limit: int = 1000) -> list[dict]:
    fields = "title,authors,year,citationCount,url,paperId,venue,publicationVenue,journal"
    data = _request_json(
        f"{SEMANTIC_SCHOLAR_API}/paper/{origin_id}/citations?fields={fields}&limit={limit}"
    )
    if not isinstance(data, dict):
        return []

    related: list[dict] = []
    for item in data.get("data") or []:
        citing = item.get("citingPaper")
        if not citing:
            continue
        related.append(_paper_summary(citing))

    related.sort(
        key=lambda item: (
            item.get("citations") if isinstance(item.get("citations"), int) else -1,
            item.get("year") or 0,
        ),
        reverse=True,
    )
    return related


def search_connected_papers(query: str, related_limit: int = 5) -> dict:
    origin = resolve_paper(query)
    if not origin:
        return {
            "query": query,
            "error": "Paper could not be resolved via Semantic Scholar.",
            "connected_papers_url": connected_papers_url(query),
        }

    origin_id = origin["paperId"]
    result = {
        "query": query,
        "origin": {
            "title": origin.get("title"),
            "authors": [author.get("name") for author in origin.get("authors", []) if author.get("name")],
            "year": origin.get("year"),
            "citations": origin.get("citationCount"),
            "url": origin.get("url"),
            "paper_id": origin_id,
            "venue": _extract_venue_from_paper(origin),
        },
        "connected_papers_url": connected_papers_url(origin.get("title"), origin_id),
        "related_papers": [],
        "source": "connected_papers",
    }

    api_key = os.environ.get("CONNECTED_PAPERS_API_KEY")
    if not api_key:
        related = _fetch_semantic_scholar_citations(origin_id)
        result["related_papers"] = related[:related_limit]
        result["source"] = "semantic_scholar_fallback"
        result["note"] = (
            "CONNECTED_PAPERS_API_KEY is not set. "
            "Related papers were fetched from Semantic Scholar citations as a fallback. "
            "Verify on https://www.connectedpapers.com/ when preparing the final report."
        )
        return result

    try:
        from connectedpapers import ConnectedPapersClient
    except ImportError:
        result["note"] = "Install connectedpapers-py to use the Connected Papers API."
        return result

    client = ConnectedPapersClient(access_token=api_key)
    graph = client.get_graph_sync(origin_id)
    if not graph or not getattr(graph, "nodes", None):
        result["note"] = "Connected Papers graph was unavailable."
        return result

    related = _collect_related_from_graph(graph, origin_id)
    result["related_papers"] = related[:related_limit]
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search Connected Papers and return related papers sorted by citations."
    )
    parser.add_argument("query", help="Paper title, arXiv URL/ID, or DOI")
    parser.add_argument(
        "--related-limit",
        type=int,
        default=5,
        help="Number of related papers to return (default: 5)",
    )
    args = parser.parse_args()

    result = search_connected_papers(args.query, related_limit=args.related_limit)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
