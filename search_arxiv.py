"""Search arXiv for papers matching a query."""

from __future__ import annotations

import argparse
import json

import arxiv


def search_arxiv(query: str, max_results: int = 20) -> list[dict]:
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
    )
    papers: list[dict] = []
    for result in client.results(search):
        published = result.published
        papers.append(
            {
                "title": result.title,
                "authors": [author.name for author in result.authors],
                "published": published.strftime("%Y-%m-%d") if published else None,
                "summary": result.summary.replace("\n", " ").strip(),
                "url": result.entry_id,
                "arxiv_id": result.get_short_id(),
                "source": "arxiv",
                "citations": None,
            }
        )
    return papers


def main() -> None:
    parser = argparse.ArgumentParser(description="Search arXiv for papers.")
    parser.add_argument("query", help="Search keywords")
    parser.add_argument(
        "--max-results",
        type=int,
        default=20,
        help="Maximum number of results (default: 20)",
    )
    args = parser.parse_args()

    papers = search_arxiv(args.query, max_results=args.max_results)
    print(json.dumps(papers, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
