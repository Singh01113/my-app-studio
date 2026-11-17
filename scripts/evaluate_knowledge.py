"""Run the five Review 1 questions against an actually imported model/index."""

import json
from pathlib import Path
import struct
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.knowledge.service import (
    KnowledgeService,
)  # pylint: disable=wrong-import-position
from app.settings import Settings  # pylint: disable=wrong-import-position

QUESTIONS = [
    "What does multi-factor authentication (MFA) mean?",
    "An urgent email asks me to sign in. What should I do before using its link?",
    "Why can MFA help after password theft, and can MFA itself be phished?",
    "Give two actions from these documents that reduce account or device risk, citing each.",
    "What is the CVSS score and fixed version for CVE-2026-99999?",
]


def main():
    """Record actual passages; the required-document test is only part of evaluation."""
    service = KnowledgeService(Settings.load().database.parent / "knowledge.sqlite3")
    results = []
    for index, question in enumerate(QUESTIONS, 1):
        answer = service.answer(question)
        documents = {e["source"]["id"] for e in answer["evidence"]}
        expected = [{"C05"}, {"C03"}, {"C05"}, {"C04"}, set()][index - 1]
        passed = expected <= documents if index < 5 else not answer["supported"]
        results.append(
            {"case": f"Q{index}", "required_document_check": passed, **answer}
        )
    with service.store.connect() as db:
        row = db.execute(
            """SELECT chunks.* FROM chunks JOIN versions
                            ON version_id=versions.id WHERE active=1 LIMIT 1"""
        ).fetchone()
        assert row and row["text"].strip()
        representation = {key: row[key] for key in ("id", "heading", "text", "tokens")}
        representation.update(
            dimensions=384,
            dtype="float32",
            first_eight_values=list(struct.unpack("384f", row["embedding"]))[:8],
        )
        assert not db.execute(
            "SELECT chunks.id FROM chunks JOIN versions ON version_id=versions.id WHERE active=1 AND length(trim(text))=0"
        ).fetchone()
    report = {
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "sources": service.store.sources(),
        "representation": representation,
        "results": results,
        "limits": "Extractive only. Required-document presence is not semantic correctness. Q4 requires C04 and an account source; manually inspect the quoted evidence.",
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
