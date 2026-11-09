# Validation record — 2026-09-30

This record distinguishes executed checks from checks that still require the user's configured environment.

## Executed successfully

| Check | Result |
|---|---|
| Python test suite | **96 passed** on Python 3.12 |
| Algorithm oracle comparisons | NetworkX 3.7: shortest paths, negative-edge DAGs, MST, articulation points, biconnected components, maximum flow |
| Additional invariants | Path cost, DFS discovery/finish nesting, flow conservation, capacity constraints, max-flow/min-cut equality, monotonic Edmonds–Karp path lengths |
| Failure cases | Invalid vertices/weights, negative-cycle effects, disconnected MST, malformed JSON, unsupported tools, oversized HTTP bodies |
| API and persistence | Flask test client with isolated SQLite test DBs; session isolation, new sessions, history, sources, and success/error tool logs |
| LCEL and routing | Actual LangChain LCEL with scripted model doubles; classifier, fallback and tool-result protocol tested |
| Anthropic SDK payload | Locally formatted `tool_use → tool_result` messages and `tool_choice: none` validated with installed ChatAnthropic/Anthropic packages; **no API request sent** |
| Real semantic ingestion | Multilingual E5 weights loaded, **479 chunks** embedded and upserted into a separate running Chroma 1.5.9 HTTP server |
| Actual vector configuration | Verified Chroma HNSW `space: cosine`, 384-dimensional E5 vectors; ready collection count 479 |
| Retrieval evaluation | Expected lecture found in top 6 for **11/11 explicit test questions**; exact queries and scores in `retrieval-evaluation.json` |
| Rule router evaluation | **12/12** labelled examples; exact queries and decisions in `router-evaluation.json` |
| UI integration | jsdom + real Flask HTTP: all 12 calculator examples, all three chat routes in fallback/demo mode, source cards, result traces, reload persistence, new session and input-error handling |
| JavaScript syntax | `node --check algotutor/static/app.js` |
| Material preparation | 11 supplied PDFs, 124 physical pages, 479 extracted slide records; every record has a printed slide number and source location |

The retrieval and router sets are small and deliberately explicit. Their perfect lecture-recall/rule-classification results are **not** measurements of general answer accuracy, natural-language coverage, model router performance or hallucination rate. Retrieval used real embeddings and Chroma; chat language-model tests used doubles.

An integration run exposed a Chroma metadata-update error: including `hnsw:space` in `modify()` is rejected even when unchanged. The implementation now updates only mutable metadata, and a subsequent full ingestion/query run passed. The cosine configuration was checked afterward.

## Not executed in this environment

- **Live Anthropic generation/classification:** no API key was configured. The API integration and payload construction are implemented, but actual model responses, access permissions, billing/quota and quality must be verified using the user's key.
- **Full Docker Compose startup / live PostgreSQL:** Docker and PostgreSQL were unavailable. SQL schema, SQLAlchemy models and Compose configuration are included; automated API tests used SQLite. The Chroma service was tested directly as a separate subprocess, outside Docker.
- **Visual browser rendering and mobile layout:** browser executable download was blocked by the environment's network allowlist. DOM/interaction checks passed, but they do not establish pixel layout or browser-specific behavior. Desktop/mobile CSS is included for local review.
- **Recorded presentation:** the demo video is not distributed in the public edition.

## Final checks on the user's machine

1. Follow README full setup and run ingestion. Check `/health`.
2. Run the three-route demo with a valid key. Confirm `generation: anthropic_lcel` and `routing.method: llm_classifier` for ordinary theory questions; explicit structured tools correctly use `explicit_input`.
3. Open a source PDF, calculate a graph, refresh history, then inspect the `tool_calls` table.
4. View the UI in Chrome/Edge at desktop and mobile widths.
5. Run `python scripts/evaluate_router.py --live` if desired; this makes paid classifier requests. Inspect mistakes rather than assume the rule-set score applies to the model.

These are concrete remaining environment-dependent checks, not assertions that the full deployment has already been tested.
