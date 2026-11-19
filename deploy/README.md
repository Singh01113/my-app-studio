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
- OpenAI generation is implemented but disabled by default pending credentials and
  explicit spending approval. Extractive fallback alone does not satisfy the course's
  real-generation requirement. See the opt-in setup below.
- The four archived CISA articles are historical educational material. Similarity
  thresholds are calibrated only on the small recorded set, not general accuracy.
- Retain `huggingface_hub==0.36.0`: a newer transitive `httpx2` installation changed
  Starlette's test-client cookie handling in this environment. Existing auth tests
  exposed it; the original `httpx` path is preserved. Its deprecation warning remains.

For an update, build the reviewed revision, reimport if preprocessing changes,
then recreate only this project service. Store the old image ID for rollback;
never delete the data directory. Hosting remains manual; CI checks do not deploy.

## Optional LLM generation: disabled until spending is approved

The app now implements OpenAI's `POST /v1/responses` through the existing httpx
client dependency. No provider SDK or new server/container is needed. The default
configurable model is `gpt-5.6-luna`; current documentation lists Responses,
structured outputs and reasoning effort `none`. Account access is not verified.
Do not assume a ChatGPT subscription gives this application API access.

**Owner setup, after explicit spending approval:**

1. In the [OpenAI API dashboard](https://platform.openai.com/), create/select a
   project, review billing and model access, and create a restricted project key
   permitting Responses requests. Set project budget alerts; alerts alone should
   not be treated as a hard spending cap. Do not paste the key into chat or Git.
2. SSH to your existing server. Edit the existing file privately, without replacing
   its hostname, origin or application signing secret:
   `~/.is373-studio/individual-review2/deploy/.env`.
   Set `OPENAI_API_KEY` to the project key and `RAG_GENERATION_MODEL=gpt-5.6-luna`.
   Keep `RAG_GENERATION_ENABLED=0` until you explicitly approve paid requests.
   Restrict file permissions: `chmod 600 deploy/.env` from that application directory.
3. Once spending is approved, set `RAG_GENERATION_ENABLED=1` and run from
   `~/.is373-studio/individual-review2`:
   `docker compose --env-file deploy/.env -f deploy/compose.yml up -d --no-build --force-recreate app`.
   A plain restart does not load changed environment variables. Recreate only this
   service; do not run `down` or touch other services. Never print `docker inspect`
   environment fields or `docker compose config`, which can expose the key.
4. Verify `/api/knowledge/sources` reports `generation_status: ready`. This means
   configured, not authenticated or proven. Execute the five-question evaluation
   below and require Q1-Q4 to return `mode: llm_generated`, a real model/usage record,
   checked citations and sensible answers. Q5 should abstain before an API call.
   Inspect every generated claim against its evidence manually. Record failures.
5. To stop paid calls, change the flag to `0` and recreate only `app` again. The
   same corpus and extractive answers continue working. Rotate a compromised key
   in the provider dashboard; never commit it or a raw environment dump.

Limits: max 20 API attempts per UTC day persisted in the knowledge database,
including failed requests; existing 5/min/client and 100/day public-query limits;
no retries; one operation at a time; 1,200 output tokens including any reasoning;
12,000 UTF-8 bytes of serialized question/passages; at most three retrieved chunks;
5-second connect and 20-second network inactivity timeouts; 64 KiB response cap.
The 20-second timeout is a network inactivity timeout, not a hard whole-request
wall-clock deadline. Browser requests time out after 30 seconds. A timed-out request
may still incur provider charges. Model changes require compatibility/cost review.

Only the current question and public retrieved passages are sent to OpenAI. No
account data, cookies, full database, key in prompt, conversation history, external
tools, web search or redirects. `store: false` requests no Responses application
storage; it is not a promise of zero provider retention. Question text is not logged
by this app. Server returns safe failure codes, never provider error bodies.

Structured claims must cite a retrieved passage ordinal and an exact quote found
in that passage. Unknown IDs, missing quotes, raw URLs/bracket references, partial
output and refusals fall back to labeled extracts. Citation links are constructed
from stored original metadata, never model-provided URLs. The model sees passages
as untrusted user data under separate higher-priority instructions; no tools exist
for an injected instruction to execute. These controls do not prove semantic
entailment or immunity to prompt injection. Human review remains necessary.

At the documented model rates ($0.20/M input, $1.20/M output), an example 2,000-input,
1,200-output-token call costs about $0.00184, or $0.0368 for 20 such calls. This is
an illustration, not an actual measured bill or guaranteed ceiling; input size,
provider pricing, other project usage and a changed model affect cost.
Sources checked during the November 2026 generation implementation:
[model and rates](https://developers.openai.com/api/docs/models/gpt-5.6-luna),
[Responses API](https://developers.openai.com/api/reference/resources/responses/methods/create),
[structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs).

After approval and activation, capture real evidence from the laptop:

```sh
.venv/bin/python scripts/evaluate_hosted_generation.py --allow-paid-generation --output docs/evidence/review2/generated-hosted-queries.json
```

This makes five public requests (normally four paid generations and one guarded
abstention). Do not run it until spending is authorized. Without the flag it
refuses a generation-enabled host. A nonzero exit with the flag means the expected
live generation journey was not established; inspect the saved failures.
