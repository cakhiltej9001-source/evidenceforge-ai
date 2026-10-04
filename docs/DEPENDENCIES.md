# Tested Phase 1-3 environment

Verified through 1 October 2026 on Windows with Python 3.12.13 and uv 0.11.13.
uv.lock is the exact resolved project/dev dependency set; uv sync --locked refuses a stale lock.
.python-version selects Python 3.12; pyproject.toml permits >=3.12,<3.15, with only 3.12 tested here.

| Package | Tested version | Role |
|---|---|---|
| evidenceforge-ai | 0.1.0 | Local package |
| langgraph | 1.2.12 | Graph execution, parallel join, reducers and serialization |
| httpx | 0.28.1 | Explicit Phase 3 dependency for streamed Tavily REST; already installed transitively |
| langchain-core | 1.6.6 | Transitive LangGraph dependency |
| langgraph-checkpoint | 4.2.0 | Transitive serializer; no SQLite service yet |
| pydantic | 2.13.5 | Boundary contracts |
| pydantic-settings | 2.15.0 | Environment/dotenv configuration |
| typing-extensions | 4.16.0 | TypedDict compatible with Pydantic |
| python-dotenv | 1.2.3 | Transitive settings dependency |
| pytest | 9.1.1 | Offline contract checks |
| ruff | 0.16.9 | Lint and formatting |
| mypy | 2.3.1 | Strict source typing |
| hatchling | 1.32.4 | Pinned wheel/source build backend |
| build | 1.6.1 | Development packaging tool |

Runtime declarations use tested minimums and major-version bounds; the lock provides exact pins
and hashes for all resolved transitive packages. The build backend is separately pinned in
build-system.requires so isolated builds use the tested backend. HTTPX is now an explicit runtime dependency, with no version change. Tavily REST uses HTTPX directly;
no Tavily SDK, document parser, SQLite checkpointer, vector store, UI or server API dependency was added.
Search receipts use the Python standard-library sqlite3 module.

LangSmith/SDK/prebuilt packages arrive transitively with LangGraph. Their presence does not mean
application tracing, a live provider or an agent workflow has been implemented or enabled.

Verified gates:
- uv sync --locked: succeeds and restores the editable local package.
- uv run --locked pytest -q: 183 passed; ordinary network connections blocked; stdlib socketpair setup permitted for Windows asyncio.
- uv run --locked ruff check .: passed.
- uv run --locked ruff format --check .: passed.
- uv run --locked mypy: passed, 33 source files.
- uv run --locked evidenceforge-check: fixture settings printed, keys excluded, cost unknown=null.
- uv build: source distribution and wheel built.
- Built wheel installed with --no-deps into the already locked environment; isolated Python import
  confirmed site-packages origin, configuration loading and state initialization.
- uv sync --locked restored editable installation afterward.
- Git ignore checks cover .env, local data, .venv and distribution artifacts.

Artifacts in ignored dist/: evidenceforge_ai-0.1.0.tar.gz and evidenceforge_ai-0.1.0-py3-none-any.whl.
The Phase 2 fixture planning graph and installed evidenceforge-plan CLI were executed. Offline
uv lock/sync/build passed without adding dependencies. The wheel contains the new modules and
planning entry point. No live model/search smoke, full research workflow, SQLite resume, semantic
factual audit or benchmark was run. These remain later milestones.


Phase 3 checks: uv lock/sync/build --offline passed; installed evidenceforge-retrieve produced one
fixture pass, one source and two exact passages with no report. Mocked Tavily contracts and receipt
replay/cancellation/budget/storage checks passed. No real search/model call or live smoke was run.

## Phase 4 environment and package verification

No dependencies were added for Phase 4. Offline uv lock and locked offline sync resolved the same
58 packages. The end-to-end graph uses the existing LangGraph/Pydantic dependencies; Markdown,
JSON and atomic output writes use the Python standard library.

Strict mypy passed for 41 source files. Ruff lint and formatting checks passed. Offline wheel/sdist
build succeeded; the wheel contains Phase 4 contracts, nodes, graph, service, renderer and the
`evidenceforge-research` entry point. The installed editable CLI exercised immediate, second-pass
and empty demos. These used synthetic fixtures only, with no real provider/search credentials.
Final regression: 201 tests passed in 100.84 seconds; details are recorded in PROGRESS.md. Phase 5 document/checkpoint packages are
not installed or implemented by this milestone.

## Phase 5 environment and package verification

The offline lock resolves 64 packages. Direct additions are pypdf 6.19.0 for PDF text extraction,
python-docx 1.2.0 for DOCX text, and langgraph-checkpoint-sqlite 3.1.1 for durable workflow
checkpoints. aiosqlite 0.22.1, lxml 6.1.3 and sqlite-vec 0.1.9 are transitive dependencies.
sqlite-vec is installed through the checkpointer but no vector retrieval is used. TXT parsing,
document storage, per-thread locks and report memory use the Python standard library.

Offline `uv lock` and `uv sync --locked` passed. Ruff lint and formatting passed; strict mypy
passed for 47 source files. The complete offline suite passed: 222 tests in 226.34 seconds.
Installed ingest, document research, and separate-process pause/resume commands passed.
`uv build --offline` produced the source distribution and wheel; the wheel contains Phase 5
modules and ingest/research entry points. No live model, web search, OCR or benchmark was run.

## Phase 6 environment and package verification

No dependencies were added. The offline lock and sync passed with the same 64 packages. Ranking,
scoped numeric comparison and graph/table projections use Python, Decimal and existing Pydantic;
the new graph node uses the installed LangGraph execution/checkpoint lifecycle. No graph database
or visualization runtime was added. The package exposes evidenceforge-inspect.

The complete offline regression passed: 254 tests in 247.93 seconds. Strict mypy passed for 54 source
files; Ruff lint and format check passed (82 files). Installed dispute research and selected-claim JSON
inspection passed. Offline wheel/sdist built; all Phase 6 analysis/node/inspection modules and the
inspection entry point were verified in the wheel. Exact results and limitations are in PROGRESS.md.

Final follow-up on 2 October 2026: the corrected offline wheel/sdist rebuild passed. Packaged Phase 6 modules match the current source byte-for-byte, and the inspection entry point is verified.
