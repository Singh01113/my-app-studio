"""Evidence retrieval and explicitly extractive responses; no simulated LLM."""

import re
import threading
import time

from app.knowledge.embedding import Embedder, MODEL_ID, MODEL_REVISION
from app.knowledge.store import Store


class KnowledgeService:
    """One embedding session per process, lazy so unrelated pages stay available."""

    def __init__(self, path):
        self.store = Store(path)
        self._embedder = None
        self._lock = threading.Lock()
        self.operation = threading.Lock()

    @property
    def embedder(self):
        """Load the real model only when import/query needs it."""
        with self._lock:
            if self._embedder is None:
                self._embedder = Embedder()
        return self._embedder

    def answer(self, question):
        """Return exact source passages; similarity does not certify an answer."""
        started = time.perf_counter()
        result = {
            "mode": "extractive",
            "model": None,
            "embedding_model": MODEL_ID,
            "embedding_revision": MODEL_REVISION,
            "question": question,
            "answer": "",
            "evidence": [],
            "supported": False,
            "limitation": (
                "Extractive evidence mode: quoted source text, not an "
                "LLM-generated answer. Four CISA sources are archived; "
                "this is a teaching corpus, not current security advice."
            ),
        }
        if not self.store.sources():
            result["answer"] = (
                "No documents have been imported yet. Please try again "
                "after the owner imports the reviewed corpus."
            )
        elif re.search(
            r"\b(cve[- ]?\d|cvss|latest|current|today|202[6-9]|"
            r"ignore.*instructions|system prompt)\b",
            question,
            re.I,
        ):
            result["answer"] = (
                "The imported sources do not establish the requested "
                "current, vulnerability-specific, or out-of-scope facts."
                " I cannot answer this from this corpus."
            )
        else:
            rows = self.store.retrieve(self.embedder.encode(question))
            evidence = [
                {key: value for key, value in row.items() if key != "metadata"}
                for row in rows
                if row["score"] >= 0.28 and rows[0]["score"] >= 0.35
            ]
            if evidence:
                result["evidence"] = evidence
                result["supported"] = True
                result["answer"] = (
                    "Relevant source excerpts (check the passages for the scope "
                    "of your question):\n\n"
                    + "\n\n".join(
                        f'[{index}] {row["text"]}'
                        for index, row in enumerate(evidence, 1)
                    )
                )
            else:
                result["answer"] = (
                    "I could not find sufficiently relevant evidence in the "
                    "imported sources. I cannot answer this from this "
                    "corpus."
                )
        result["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
        return result
