"""Transactional immutable source versions and sqlite-vec cosine retrieval."""

from contextlib import contextmanager
import hashlib
import json
import math
import struct
from pathlib import Path
import sqlite3
import time

import sqlite_vec


class Store:
    """Small exact vector index, kept separate from authentication data."""

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS versions (
                    id TEXT PRIMARY KEY, doc_id TEXT NOT NULL, metadata TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY, version_id TEXT NOT NULL REFERENCES versions(id),
                    heading TEXT NOT NULL, text TEXT NOT NULL, tokens INTEGER NOT NULL,
                    embedding BLOB NOT NULL CHECK(length(embedding)=1536));
                CREATE INDEX IF NOT EXISTS chunk_versions ON chunks(version_id);
                CREATE TABLE IF NOT EXISTS budgets (
                    bucket TEXT PRIMARY KEY, count INTEGER NOT NULL, expires INTEGER NOT NULL);
            """)

    @contextmanager
    def connect(self):
        """Use bounded SQLite locking and load only the installed vector extension."""
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        if hasattr(db, "enable_load_extension"):
            db.enable_load_extension(True)
            sqlite_vec.load(db)
            db.enable_load_extension(False)
        else:
            # macOS framework Python disables extension loading. Same exact metric.
            db.create_function("vec_distance_cosine", 2, cosine_distance)
        try:
            with db:
                yield db
        finally:
            db.close()

    def import_document(self, document, embedder):
        """Embed before a transaction; failed indexing never changes active data."""
        version = document["id"] + ":" + document["content_hash"]
        with self.connect() as db:
            exists = db.execute(
                "SELECT id FROM versions WHERE id=?", (version,)
            ).fetchone()
        chunks = []
        if not exists:
            for number, chunk in enumerate(embedder.chunks(document["sections"])):
                if number >= 100:
                    raise ValueError("Document exceeds the 100 chunk limit.")
                if not chunk["text"].strip():
                    raise ValueError("Empty evidence chunk rejected.")
                vector = embedder.encode(
                    document["title"] + ": " + chunk["heading"] + ": " + chunk["text"]
                )
                chunks.append(
                    (
                        version + f":{number:03}",
                        version,
                        chunk["heading"],
                        chunk["text"],
                        chunk["token_count"],
                        vector,
                    )
                )
        metadata = {key: value for key, value in document.items() if key != "sections"}
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            cursor = db.execute(
                "INSERT OR IGNORE INTO versions VALUES (?,?,?,0)",
                (version, document["id"], json.dumps(metadata)),
            )
            added = len(chunks) if cursor.rowcount else 0
            if added:
                db.executemany("INSERT INTO chunks VALUES (?,?,?,?,?,?)", chunks)
            db.execute("UPDATE versions SET active=0 WHERE doc_id=?", (document["id"],))
            db.execute("UPDATE versions SET active=1 WHERE id=?", (version,))
        return {"document": document["id"], "version": version, "added_chunks": added}

    def sources(self):
        """Expose provenance and counts, never private database paths."""
        with self.connect() as db:
            rows = db.execute(
                """SELECT metadata, count(chunks.id) AS chunks FROM versions
                JOIN chunks ON chunks.version_id=versions.id
                WHERE active=1 GROUP BY versions.id
                ORDER BY doc_id"""
            ).fetchall()
        return [
            {**json.loads(row["metadata"]), "chunks": row["chunks"]} for row in rows
        ]

    def retrieve(self, vector, top_k=3, current_only=False):
        """Exact cosine scan over active versions; bounded teaching corpus only."""
        with self.connect() as db:
            rows = db.execute(
                """SELECT chunks.id, heading, text, tokens, metadata,
                1-vec_distance_cosine(embedding, ?) AS score FROM chunks
                JOIN versions ON version_id=versions.id WHERE active=1
                AND (?=0 OR json_extract(metadata,'$.archived')=0)
                ORDER BY score DESC, chunks.id LIMIT ?""",
                (vector, current_only, top_k),
            ).fetchall()
        return [{**dict(row), "source": json.loads(row["metadata"])} for row in rows]

    def consume_budget(self, client):
        """Persistent 5/minute per client and 100/day overall, with no raw IP log."""
        now = int(time.time())
        digest = hashlib.sha256(client.encode()).hexdigest()
        buckets = [
            (f"ip:{digest}:{now // 60}", 5, (now // 60 + 1) * 60),
            (f"day:{now // 86400}", 100, (now // 86400 + 1) * 86400),
        ]
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM budgets WHERE expires<=?", (now,))
            for bucket, limit, expires in buckets:
                row = db.execute(
                    "SELECT count FROM budgets WHERE bucket=?", (bucket,)
                ).fetchone()
                if row and row[0] >= limit:
                    return False
                db.execute(
                    "INSERT INTO budgets VALUES (?,1,?) ON CONFLICT(bucket) "
                    "DO UPDATE SET count=count+1",
                    (bucket, expires),
                )
        return True


def cosine_distance(left, right):
    """Exact fallback for Python builds without SQLite loadable extensions."""
    a, b = struct.unpack("384f", left), struct.unpack("384f", right)
    denominator = math.sqrt(sum(x * x for x in a) * sum(x * x for x in b))
    return 1 - sum(x * y for x, y in zip(a, b)) / max(denominator, 1e-12)
