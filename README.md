# AlgoTutor

A Hebrew-first tutor for the supplied **11 algorithms lectures**, with **12 deterministic Python tools**, source citations and step-by-step graph visualizations. Plain HTML/CSS/JavaScript frontend, Flask backend, PostgreSQL history, separate Chroma vector service, Anthropic tool calling and LangChain LCEL.

Full Hebrew guide: [README_HE.md](README_HE.md). Beginner Windows guide: [START_HERE_HE.md](START_HERE_HE.md).

## Full deployment (academic submission)

Prerequisites: Docker Desktop with Linux containers and Compose, Python 3.12 for setup, network access for initial downloads, and an active Anthropic API key. The key is a separate API credential, not a chat subscription.

From the `AlgoTutor` folder:

```bash
python scripts/setup.py
# Edit .env: set ANTHROPIC_API_KEY. Do not put the key in frontend code.
docker compose up --build -d
python scripts/prepare_materials.py  # Only after locally adding authorized lecture PDFs
docker compose exec app python scripts/ingest.py
```

Open **http://localhost:5000**. Check http://localhost:5000/health. Full readiness requires DB connectivity, an indexed collection and a configured API key. A `configured` key has not been authenticated by `/health`; send a chat request to verify access and quota.

The initial image build and model download may take several minutes. Model weights, PostgreSQL data and Chroma data persist in separate named volumes. `docker compose down` stops services while retaining their data. Ingestion uses upsert and removes stale chunks only after a successful complete indexing pass.

`scripts/setup.py` generates random DB/session secrets and never overwrites an existing `.env`. On Windows, use `py -3.12` if `python` is unavailable. Container addresses are `db:5432` and `chroma:8000`; local development uses `localhost:5433` and `localhost:8000`.

## Local Flask / PyCharm development, real databases in Docker

Select Python 3.12 in a virtual environment as the PyCharm interpreter, create `.env`, then:

```bash
.venv/bin/python -m pip install torch==2.14.0 --index-url https://download.pytorch.org/whl/cpu
.venv/bin/python -m pip install -r requirements.txt
docker compose up -d db chroma
.venv/bin/python scripts/ingest.py
.venv/bin/python run.py
```

Do not also run the Compose `app` service on the same port. `run.py` is the development server; the Docker app uses Gunicorn with one worker and four threads.

## Algorithms and input contract

| Lecture | Tool | Main output |
|---|---|---|
| 1 | `graph_scan` | Vertices, edges, adjacency lists |
| 2 | `bfs` | Unweighted distances, paths, visit order, tree |
| 3 | `dijkstra` | Nonnegative shortest paths and relaxation trace |
| 4 | `bellman_ford` | Negative-edge shortest paths, reachable negative-cycle effects |
| 5 | `floyd_warshall` | All-pairs distances and reconstructed paths |
| 6 | `prim` | Minimum spanning tree and weight |
| 7 | `kruskal` | MST with Union-Find and accept/reject trace |
| 7 | `union_find` | Representatives and groups after operations |
| 8 | `dfs` | DFS forest, parent pointers, discovery/finish times |
| 9 | `biconnected` | Articulation points, low values, vertex-biconnected edge blocks |
| 10 | `ford_fulkerson` | Augmenting paths, max flow, residual network and min cut |
| 11 | `edmonds_karp` | BFS augmenting paths, max flow and min cut |

Teaching implementations are independent code for the lecture topics, not literal transcriptions of lecture pseudocode. Input order breaks ties. Different valid traversal/MST choices may result from a different neighbor order.

Graphs contain 1–16 string-labelled vertices and at most 60 edges. No parallel edges; enter an undirected edge once. Weights must be finite numbers of absolute value at most 1,000,000. Dijkstra rejects negative weights, BFS ignores weights, and MST tools reject directed or disconnected graphs. Flow requires a directed graph, distinct source/sink, no self-loops and integer capacities 0–50 in `weight`; antiparallel edges are supported. Union-Find accepts up to 30 elements and 100 operations.

`null` distance means unreachable. `"-infinity"` means a negative cycle makes the shortest distance unbounded, so no shortest path is returned. Isolated vertices are listed separately from biconnected edge blocks. Flow returns the complete final result even if its displayed augmentation trace is capped at 250 steps.

The UI supports comma-separated vertices, one edge per line (`A B 4`), and advanced JSON. When the JSON editor is expanded, it is the authoritative input. No image-to-graph recognition is implemented.

## Retrieval and citation fidelity

The original (not publicly bundled) PDFs contain four slides per physical page. `scripts/prepare_materials.py` uses Poppler to extract each quadrant in Hebrew reading order, removes bidi controls and normalizes a known font encoding error and selected mathematical glyphs. It preserves lecture, physical PDF page, printed slide number and quadrant. The original local course corpus contained **124 PDF pages and 479 extracted slide records**; these files are omitted from GitHub.

`scripts/ingest.py` uses E5 tokenizer offsets to create overlapping chunks within the 512-token limit, including title/prefix overhead. Documents use `passage:` and queries use `query:`. Embeddings are normalized, with cosine distance in Chroma. Up to six distinct slides are returned with `score = 1 - distance`. Scores indicate retrieval similarity, **not answer confidence**. Change `CHROMA_COLLECTION` and re-index if changing the embedding model.

Figures and some formulas do not survive text extraction. RAG must acknowledge missing evidence and cannot infer diagram edges from unavailable pixels. PDF links allow source inspection. No OCR or diagram transcription is claimed.

## Routing, memory, tools and fallback

Every `/chat` request runs the router. Explicit structured algorithm requests select tools deterministically. Otherwise, an LLM structured classifier chooses `rag`, `tools` or `direct` and rewrites follow-up questions using history. A rule-based fallback is clearly exposed if model routing is unavailable. Theory questions about algorithms route to RAG.

Anthropic-native tool definitions live in `algotutor/catalog.py`. The server executes whitelisted functions, validates the input, records actual inputs/outputs, sends `ToolMessage` results back to the model and synthesizes the final answer through `ChatPromptTemplate | ChatAnthropic | StrOutputParser`. Model calls have timeouts and two retries. Failures preserve completed calculations and return labelled deterministic summaries or source snippets. No fallback pretends to be a generated answer.

History is scoped to a signed HttpOnly, SameSite cookie. PostgreSQL stores messages and their structured payloads, including routes and sources. The last 12 bounded messages enter the model context; `/history` returns the last 100. New chat creates a new session; previous messages remain stored but the UI does not expose a session browser. There is no account system. Per-session process locks assume the supplied single-worker configuration; multiple workers need a shared lock design.

## Tests and evaluation

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest
docker compose exec app python scripts/evaluate_retrieval.py
```

Tests compare results with NetworkX, cover seeded random graphs, negative cycles, path costs, flow conservation, min-cut equality, low-link structure, invalid inputs, session isolation, HTTP errors and the LCEL/tool protocol using scripted model doubles. SQLite is a test dependency only. See [docs/VALIDATION.md](docs/VALIDATION.md) for exactly what was and was not verified in the development environment.

The retrieval evaluation measures lecture recall at six on a small explicit 11-question set. It does not measure answer quality, hallucination rate or generalization. The separate router evaluation uses a small labelled bilingual query set and reports rule/LLM accuracy without claiming a production benchmark.

Run `python scripts/evaluate_router.py` for free rule-based evaluation, or add `--live` to use the configured paid API. Optional UI integration checks: install Node.js, run `npm install`, set `ALGO_PYTHON` to the virtual environment's Python executable and run `npm run test:ui`. These use jsdom against real Flask HTTP endpoints, not a browser renderer.

## Layout and documentation

- `algotutor/`: algorithms, schemas, router, LCEL, retrieval, persistence, API and UI.
- `data/lectures/`: authorized PDFs added locally; `data/processed/`: locally generated extraction data. Both are ignored by Git.
- `migrations/001_init.sql`: initial PostgreSQL schema, run on a fresh Docker volume.
- `scripts/`: setup, extraction, ingestion and evaluations.
- `tests/`: unit/integration tests; `docs/`: architecture, API, presentation script, validation and reflection template.

See the [architecture](docs/ARCHITECTURE.md) and [API contract](docs/API.md). The personal reflection and demo video are not distributed in the public repository.

## Troubleshooting

| Symptom | Action |
|---|---|
| Missing `docker` | Install/start Docker Desktop, then reopen the terminal |
| Missing secrets | Run `scripts/setup.py`; repair existing `.env` using `.env.example` |
| Empty collection | Wait for Chroma and run the ingestion command |
| Chroma connection fails | Inspect `docker compose ps` and `docker compose logs --tail 80 chroma` |
| Model download fails | Check Hugging Face access and retry ingestion |
| Anthropic 401/403 | Verify API key and access to the configured model |
| 429/service failure | Retry later; the UI labels grounded fallback responses |
| Port 5000 occupied | Stop the previous Flask/app process |

## Attribution and primary documentation

The original lecture slides are by **Prof. Amos Israeli**. Rights remain with the author and the slides are not distributed in this public repository. The bundled example graphs were created for the app and are not claimed to be original lecture figures.

[LangChain ChatAnthropic](https://docs.langchain.com/oss/python/integrations/chat/anthropic) · [Anthropic tool definitions](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools) · [E5 model card](https://huggingface.co/intfloat/multilingual-e5-small) · [Chroma](https://docs.trychroma.com/) · [Flask](https://flask.palletsprojects.com/)
