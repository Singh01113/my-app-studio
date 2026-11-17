"""Executed baseline, chunk-size and archive-filter comparisons on the same corpus."""

import json
from pathlib import Path
import re
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.knowledge import corpus  # pylint: disable=wrong-import-position
from app.knowledge.service import (
    KnowledgeService,
)  # pylint: disable=wrong-import-position
from app.knowledge.store import Store  # pylint: disable=wrong-import-position
from scripts.evaluate_knowledge import (
    QUESTIONS,
)  # pylint: disable=wrong-import-position


def main():
    """Keep queries/model constant; never substitute expected outputs for retrieval."""
    service = KnowledgeService("runtime/knowledge.sqlite3")
    with service.store.connect() as db:
        chunks = [
            dict(r)
            for r in db.execute("""SELECT chunks.id, text, heading, doc_id, metadata
            FROM chunks JOIN versions ON version_id=versions.id WHERE active=1""")
        ]
    results = []
    for question in QUESTIONS:
        terms = set(re.findall(r"[a-z]+", question.lower()))
        ranked = sorted(
            chunks,
            key=lambda row: (
                -len(
                    terms
                    & set(
                        re.findall(
                            r"[a-z]+",
                            (
                                json.loads(row["metadata"])["title"]
                                + " "
                                + row["heading"]
                                + " "
                                + row["text"]
                            ).lower(),
                        )
                    )
                ),
                row["id"],
            ),
        )[:3]
        vector = service.embedder.encode(question)
        results.append(
            {
                "question": question,
                "keyword_overlap_top3": [r["id"] for r in ranked],
                "vector_200_top3": [r["id"] for r in service.store.retrieve(vector)],
                "current_only_top3": [
                    r["id"] for r in service.store.retrieve(vector, current_only=True)
                ],
            }
        )

    class SmallerChunks:
        """Same real embedding model with a different chunk boundary only."""

        def chunks(self, sections):
            return service.embedder.chunks(sections, size=120, overlap=20)

        def encode(self, text):
            return service.embedder.encode(text)

    with tempfile.TemporaryDirectory() as directory:
        store = Store(Path(directory) / "comparison.sqlite3")
        for source in corpus.SOURCES.values():
            html = Path(f"runtime/review2-sources/{source['id']}.html").read_text()
            store.import_document(corpus.extract(source, html), SmallerChunks())
        for result in results:
            result["vector_120_top3"] = [
                r["id"]
                for r in store.retrieve(service.embedder.encode(result["question"]))
            ]
        small_count = sum(s["chunks"] for s in store.sources())
    print(
        json.dumps(
            {
                "model": "MiniLM fixed revision; same questions and sources",
                "chunk_counts": {
                    "200_tokens_30_overlap": len(chunks),
                    "120_tokens_20_overlap": small_count,
                },
                "results": results,
                "limitations": "Raw retrieval even for Q5; the answering layer must still abstain. Top-3 IDs alone do not prove answer correctness.",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
