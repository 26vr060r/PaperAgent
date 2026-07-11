"""Search Google Scholar for papers with citation counts."""

from __future__ import annotations

import argparse
import json
import time


def search_scholar(query: str, max_results: int = 20, delay: float = 2.0) -> list[dict]:
    from scholarly import scholarly

    papers: list[dict] = []
    search = scholarly.search_pubs(query)
    for index, pub in enumerate(search):
        if index >= max_results:
            break
        bib = pub.get("bib", {})
        papers.append(
            {
                "title": bib.get("title"),
                "authors": bib.get("author", []),
                "published": bib.get("pub_year"),
                "summary": bib.get("abstract"),
                "url": pub.get("pub_url") or pub.get("eprint_url"),
                "source": "google_scholar",
                "citations": pub.get("num_citations", 0),
            }
        )
        if delay > 0 and index + 1 < max_results:
            time.sleep(delay)
    return papers


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search Google Scholar (scholar.google.jp backend) for papers."
    )
    parser.add_argument("query", help="Search keywords")
    parser.add_argument(
        "--max-results",
        type=int,
        default=20,
        help="Maximum number of results (default: 20)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay between requests in seconds (default: 2.0)",
    )
    args = parser.parse_args()

    papers = search_scholar(args.query, max_results=args.max_results, delay=args.delay)
    print(json.dumps(papers, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
