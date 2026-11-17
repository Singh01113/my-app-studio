# Review 2 application deployment

This is a bounded application deployment, separate from the calculator and other
Server Studio services. It adds one service to the existing `hosting-web` network.
Do not reuse an existing hostname or edit the proxy. `deploy/compose.yml` owns only
Compose project `amman-review2`; no host port is published.

## Repeatable setup

1. Run `python3 studio.py setup` and `python3 studio.py check` locally.
2. Run `.venv/bin/python scripts/setup_model.py`. It downloads the pinned MiniLM
   ONNX/tokenizer files. The application checks both SHA-256 hashes before loading.
3. Run `.venv/bin/python scripts/import_knowledge.py` to fetch the allowlisted
   original sources. If an agency blocks the host, the trusted owner can supply
   verified HTML snapshots using `--snapshots PATH`; the public API cannot accept
   file paths or URLs. Keep downloads and runtime data out of Git.
4. Transfer only application/build files to a new scoped server directory, plus
   the public model files under `deploy/models` and the selected snapshots if
   needed. Do not transfer your local auth database, development key or `.env`.
5. Create a private `deploy/.env` from the example. Set the new HTTPS hostname and
   origin. Generate a random server-only secret, for example with Python's
   `secrets.token_urlsafe(48)`; never paste it into the record or commit it.
6. Make `deploy/data` writable by UID/GID 10001 and the public model directory
   readable by that user. Build with
   `docker compose --env-file deploy/.env -f deploy/compose.yml build`.
7. Use the same Compose prefix with `run --rm --no-deps app python
   scripts/import_knowledge.py` to initialize the persistent index, then `up -d
   --no-build app`. A verified snapshots directory may be mounted read-only at
   `/sources` and passed to the CLI if required. A one-time root helper with only
   CHOWN capability can assign the new data directory; the serving application
   remains unprivileged with all capabilities dropped.
8. Verify `/health`, `/portfolio`, `/assistant`, `/api/knowledge/sources` and a
   real question. Restart **only** this service with the same Compose prefix and
   `restart app`; compare source counts and a repeated answer afterward.
9. Compare selected identities/start times/restart counts/ports of existing
   containers against the pre-deployment snapshot. Never restart the proxy or
   run a global prune/down operation.

## Runtime limits and operations

- One process, 0.75 CPU, 320 MiB container memory, 128 PIDs, read-only root filesystem.
- Persistent auth database and separate knowledge SQLite file in `deploy/data`;
  model files mounted read-only. Back up this directory privately while the app
  is stopped or using SQLite's backup API. Restore verification is not yet done.
- Five reviewed documents; 100 chunks maximum per document; actual corpus is much
  smaller. Embeddings are 384-dimensional float32, exact cosine search.
- Query text is limited to 1,000 characters and the model to 256 input tokens.
  A long tokenized query can receive a retrieval error; shorten it and retry.
- Persistent limits: 5 queries/minute per server-observed client, 100/day overall.
  Proxy forwarding is not broadly trusted. Clients can share the proxy's bucket;
  this is conservative and may cause early throttling. No raw questions are logged.
- One import/query operation at a time. Imports require the current admin role
  and session CSRF; roles can only be set through the trusted existing CLI.
- No generation model/provider is configured. The hosted output is explicitly
  extractive. This does **not** satisfy the course's real-generation requirement.
- The four archived CISA articles are historical educational material. Similarity
  thresholds are calibrated only on the small recorded set, not general accuracy.
- Retain `huggingface_hub==0.36.0`: a newer transitive `httpx2` installation changed
  Starlette's test-client cookie handling in this environment. Existing auth tests
  exposed it; the original `httpx` path is preserved. Its deprecation warning remains.

For an update, build the reviewed revision, reimport if preprocessing changes,
then recreate only this project service. Store the old image ID for rollback;
never delete the data directory. Hosting remains manual; CI checks do not deploy.
