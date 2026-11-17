"""Vector storage and HTTP boundary regressions; synthetic embeddings are fixtures."""

from concurrent.futures import ThreadPoolExecutor
import hashlib
import struct

import httpx
import pytest

from app import database
from app.knowledge import corpus
from app.knowledge.store import Store
from tests.test_accounts import sign_in


class FixtureEmbedder:
    """Deterministic test vectors only; real model evaluated in the evidence script."""

    def chunks(self, sections):
        for section in sections:
            yield {**section, "token_count": 12}

    def encode(self, text):
        vector = [0.0] * 384
        vector[0 if "password" in text else 1] = 1.0
        return struct.pack("384f", *vector)


def document(text="Use unique passwords."):
    """An explicitly synthetic document used only in isolated test databases."""
    return {
        **corpus.SOURCES["C01"],
        "content_hash": hashlib.sha256(text.encode()).hexdigest(),
        "accessed_at": "2026-11-17T00:00:00+00:00",
        "sections": [{"heading": "Test fixture", "text": text}],
    }


def test_repeat_concurrent_import_restart_and_version_switch(tmp_path):
    """Retries and racing imports add no duplicate rows; old versions stay inactive."""
    path = tmp_path / "knowledge.sqlite3"
    store, embedder = Store(path), FixtureEmbedder()
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(
            pool.map(lambda _: store.import_document(document(), embedder), range(2))
        )
    assert sum(row["added_chunks"] for row in outcomes) == 1
    reopened = Store(path)
    assert reopened.sources()[0]["chunks"] == 1
    assert reopened.import_document(document(), embedder)["added_chunks"] == 0
    reopened.import_document(document("Install software updates."), embedder)
    results = reopened.retrieve(embedder.encode("software"))
    assert len(results) == 1 and results[0]["text"] == "Install software updates."
    with reopened.connect() as db:
        assert db.execute("SELECT count(*) FROM versions").fetchone()[0] == 2


def test_failed_embedding_preserves_active_version(tmp_path):
    """Embedding failure cannot replace the last working corpus."""
    store = Store(tmp_path / "index.sqlite3")
    embedder = FixtureEmbedder()
    store.import_document(document(), embedder)

    class Broken(FixtureEmbedder):
        def encode(self, text):
            raise ValueError("Synthetic model failure")

    with pytest.raises(ValueError):
        store.import_document(document("new text"), Broken())
    assert (
        store.retrieve(embedder.encode("password"))[0]["text"]
        == "Use unique passwords."
    )


def test_import_permissions_csrf_demotion_and_allowlist(client, settings, monkeypatch):
    """The same session loses importer access immediately after demotion."""
    endpoint = "/api/knowledge/import"
    payload = {"document_id": "C01"}
    assert client.post(endpoint, json=payload).status_code == 401
    sign_in(client)
    assert client.post(endpoint, json=payload).status_code == 403
    database.set_role(settings, "route_member", "admin")
    assert client.post(endpoint, json=payload).status_code == 403
    token = client.get("/api/csrf").json()["csrf_token"]
    headers = {"X-CSRF-Token": token}
    service = client.app.state.knowledge
    monkeypatch.setattr(service, "_embedder", FixtureEmbedder())
    monkeypatch.setattr(corpus, "fetch_source", lambda _: "fixture")
    monkeypatch.setattr(corpus, "extract", lambda *_: document())
    assert (
        client.post(endpoint, json=payload, headers=headers).json()["added_chunks"] == 1
    )
    assert (
        client.post(endpoint, json=payload, headers=headers).json()["added_chunks"] == 0
    )
    assert (
        client.post(endpoint, json={"document_id": "C99"}, headers=headers).status_code
        == 422
    )
    assert (
        client.post(
            endpoint, json={**payload, "url": "http://localhost"}, headers=headers
        ).status_code
        == 422
    )
    database.set_role(settings, "route_member", "member")
    assert client.post(endpoint, json=payload, headers=headers).status_code == 403


def test_query_citations_abstention_limits_and_persistence(client, monkeypatch):
    """Public answers quote real stored fixture text and never invent vulnerability data."""
    service = client.app.state.knowledge
    monkeypatch.setattr(service, "_embedder", FixtureEmbedder())
    service.store.import_document(document(), service.embedder)
    result = client.post(
        "/api/knowledge/query", json={"question": "password advice"}
    ).json()
    assert result["mode"] == "extractive" and result["model"] is None
    assert result["evidence"][0]["text"] in result["answer"]
    assert result["evidence"][0]["source"]["url"] == corpus.SOURCES["C01"]["url"]
    for question in ["What is CVE-2026-99999?", "What is current policy?"]:
        answer = client.post("/api/knowledge/query", json={"question": question}).json()
        assert not answer["supported"] and not answer["evidence"]
    for _ in range(2):
        assert (
            client.post(
                "/api/knowledge/query", json={"question": "password advice"}
            ).status_code
            == 200
        )
    assert (
        client.post(
            "/api/knowledge/query", json={"question": "password advice"}
        ).status_code
        == 429
    )
    reopened = Store(service.store.path)
    assert not reopened.consume_budget("testclient")
    assert (
        client.post("/api/knowledge/query", json={"question": "x" * 1001}).status_code
        == 422
    )


def test_empty_corpus_and_public_pages(client):
    """An uninitialized corpus is explicit; public pages need no account."""
    for path in ["/portfolio", "/assistant", "/api/knowledge/sources"]:
        assert client.get(path).status_code == 200
    response = client.post("/api/knowledge/query", json={"question": "What is MFA?"})
    assert "No documents" in response.json()["answer"]
    assert "Extractive evidence mode" in client.get("/assistant").text


def test_import_fetch_failure_is_helpful(client, settings, monkeypatch):
    """Network failure returns a recoverable error without leaking provider details."""
    sign_in(client)
    database.set_role(settings, "route_member", "admin")
    token = client.get("/api/csrf").json()["csrf_token"]

    def fail(_):
        raise httpx.ConnectError("unavailable")

    monkeypatch.setattr(corpus, "fetch_source", fail)
    response = client.post(
        "/api/knowledge/import",
        json={"document_id": "C01"},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 502
    assert "previous active source" in response.json()["detail"]
