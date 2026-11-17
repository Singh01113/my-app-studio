"""Trusted owner CLI: import only the reviewed corpus, without creating an admin account."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.knowledge import corpus  # pylint: disable=wrong-import-position
from app.knowledge.service import (
    KnowledgeService,
)  # pylint: disable=wrong-import-position
from app.settings import Settings  # pylint: disable=wrong-import-position


def main():
    """Local snapshots are owner-only input; the public API never accepts paths."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshots", type=Path)
    args = parser.parse_args()
    service = KnowledgeService(Settings.load().database.parent / "knowledge.sqlite3")
    results = []
    for source in corpus.SOURCES.values():
        html = (
            (args.snapshots / (source["id"] + ".html")).read_text()
            if args.snapshots
            else corpus.fetch_source(source)
        )
        document = corpus.extract(source, html)
        results.append(service.store.import_document(document, service.embedder))
    print(
        json.dumps({"imports": results, "sources": service.store.sources()}, indent=2)
    )


if __name__ == "__main__":
    main()
