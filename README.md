# Video Analyzer

An agency-first footage library with Gemini video analysis, editable shot metadata, and portable editorial handoffs. Built for finding and reusing footage across client projects, with a deeper analysis workspace for filmmakers.

## What works

- **Persistent library:** SQLite stores assets, analysis results, annotations, project/client/campaign data, collections, rights status, and review decisions across restarts.
- **Local-first import:** import multiple videos without an AI key; ffprobe reads source duration, resolution, codec, frame rate, audio presence and embedded timecode. ffmpeg produces actual footage posters and shot thumbnails.
- **Footage discovery:** search filenames, human metadata and AI descriptions across the library or individual shots. Search is currently keyword matching, with project, review, tag and rights filters; it is not a vector/semantic search engine.
- **Progressive analysis:** known-duration videos are indexed in 30-second processing sections. Shots and thumbnails appear as each section finishes, with successful section counts and source time processed. These section edges are not claimed to be editorial cuts. Gemini proposes shots, subjects, actions, visible text, logos, location, cinematography and timestamped evidence. Human tags/notes remain separate. The full preset adds detailed notes, summary and related shots afterward.
- **Background processing:** analysis continues when a library tab closes, progress and completed stages persist, duplicate runs are rejected, and interrupted runs are identified on restart. Retry is explicit; a restart does not automatically resume external model calls.
- **Editorial review:** preview source footage, seek to a matched shot, edit tags and notes, record rights and review status, and distinguish approximate AI timestamps from source technical facts.
- **Portable exports:** JSON, UTF-8 CSV, XMP with timed markers, transcript SRT, and guarded EDL/FCPXML reference exports. Source media remains unchanged.
- **Original analyzer:** the earlier scene timeline, detail, comparison and report views remain available from **Analyzer**.

## Run locally

Requirements: Python 3.11+, Node.js 20.19+ or 22.12+, and ffmpeg/ffprobe on PATH.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
npm --prefix frontend ci
npm --prefix frontend run build
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Open [the local workspace](http://127.0.0.1:8000). The backend serves the built frontend, so one server is enough.

### macOS / Linux

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
npm --prefix frontend ci
npm --prefix frontend run build
.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

For frontend development, run the backend on port 8000 and `npm --prefix frontend run dev` in another terminal. Vite proxies `/api` to the backend.

### Gemini configuration

Create an ignored `.env.local` or `.env` in the repository root (see `.env.example`):

```dotenv
GOOGLE_API_KEY=your-key-here
GEMINI_ANALYSIS_MODEL=gemini-3.8-flash
GEMINI_DEEP_MODEL=gemini-3.8-flash
```

The model defaults were selected from official documentation current in September 2026. They are configurable because availability, pricing and quality change. Verify access and benchmark representative footage before bulk processing. Both presets initially use the same stable model; the full preset performs more analysis passes.

Restart the backend after changing `.env.local` or `.env`. Alternatively use **Workspace settings** to supply a personal key. Browser keys are saved in browser localStorage and transmitted in headers to this application's backend, which calls Google. They are not placed in analysis URLs or saved in the library database. Importing/organizing footage does not send it to Google; starting analysis does.

Both Gemini presets passed a live smoke test with the configured key on a synthetic six-second, two-shot clip. Both identified the two exact on-screen labels and produced no invented transcript for silent footage. This verifies API compatibility; representative agency/filmmaker accuracy and comparative model performance remain unbenchmarked. See `docs/VERIFICATION.md`.

### Docker

```bash
docker compose up --build
```

Open [the Docker workspace](http://localhost:5173). Compose binds to loopback and persists both the library database and media in separate volumes. Run one API worker for this local workspace.

## Storage and processing

| Item | Default location / behavior |
|---|---|
| Original videos and thumbnails | `backend/uploads/` (ignored by Git) |
| Library and analysis records | `backend/data/library.sqlite3` (ignored by Git) |
| Provider key | `.env.local` / `.env` or optional browser override; never in SQLite |
| Upload limit | 2,000 MiB per file; configurable via `MAX_FILE_SIZE_MB` |
| Analysis concurrency | Two jobs; configurable via `MAX_CONCURRENT_ANALYSES` |
| Google file retention | Expiring provider references are refreshed from local originals before analysis |
| Results | Durable after each processing section; partial shots are searchable and reviewable during analysis. Failed sections retain successful results and report incomplete coverage. |

`DATABASE_PATH` and `UPLOAD_DIR` can override storage locations. Back up both the database and originals; exports do not package video files. YouTube references support analysis but do not provide local technical metadata or a native preview; use a local original for reliable editorial handoffs.

## Accuracy and export boundaries

AI scene/shot boundaries are **approximate**. Sampling can miss short edits; decimal timestamps do not imply frame accuracy. Model confidence is an uncalibrated estimate, and visible branding does not establish usage rights. Speech text is model transcription with shot-level timing, not a verified word-aligned transcript. SRT export fails clearly when no actual timed transcript exists; it never turns shot descriptions into subtitles.

Progressive indexing still waits for Google's upload processing before the first section. Shots crossing processing boundaries may be split and are flagged for review. Retry currently reprocesses the run; it does not skip successful sections. See [progressive analysis](docs/PROGRESSIVE_ANALYSIS.md) for behavior and measured latency.

EDL/FCPXML exports require verified source frame rate and embedded source timecode. Fractional/drop-frame sources are deliberately rejected by the current adapter. FCPXML also needs valid source dimensions and references the original filename relative to the exported XML; put the original beside the XML or relink in the editor. Generated structures are tested, but import/round-trip behavior in Premiere, Resolve and Final Cut Pro has not been tested in installed editors.

Cost figures use recorded provider token usage and dated pricing where available. Thinking tokens are included; audio/context/cache/pricing differences can make an aggregate estimate incomplete. Unknown models are marked unpriced, not assigned a zero-dollar promise.

This release is a **single-user local workspace**. Shared agency deployment still needs authentication, tenant boundaries, permission checks, object storage, a separate durable worker queue, operational monitoring and audit trails. The research and roadmap specify those changes; do not expose the unauthenticated local API as a public service.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pip install pytest httpx
.\.venv\Scripts\python.exe -m pytest backend/tests tests -q
npm --prefix frontend run build
npm --prefix frontend run lint
```

Tests exercise real ffmpeg import/probe/poster generation and range playback, durable storage, metadata validation, search/review behavior, job recovery, mocked analysis stages, timestamp validation, provenance and export formatting. A source corpus with human ground truth is still needed for model accuracy comparisons.

## Research and implementation decisions

Start with [the research brief](docs/research/README.md), then read:

- [Model landscape and architecture](docs/research/model-landscape.md)
- [Agency and filmmaker workflows / competitor analysis](docs/research/workflows-and-market.md)
- [Product roadmap and release gates](docs/ROADMAP.md)

The research compares Gemini, Twelve Labs, cloud indexers and open models, plus Premiere, Resolve, Final Cut, Frame.io, iconik and axle. It distinguishes vendor claims from verified capabilities and recommendations. No universal model winner is assumed.

## Stack

React 19 / TypeScript / Vite / Zustand; Python / FastAPI / Pydantic; SQLite; Google Gen AI SDK; ffmpeg / ffprobe. API docs are available at `/docs` while the server runs.
