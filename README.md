# Video Analyzer

AI-powered video analysis tool that breaks down any video into scenes, shots, and detailed metadata using Google Gemini.

Upload a video (or paste a YouTube URL), and get a full structural breakdown: scene detection, cinematography analysis, shot matching, custom AI prompts, and export to EDL/XML for your NLE.

## Features

- **3-pass AI analysis** — Scene detection (Flash), deep per-scene analysis (Pro), full summary (Pro)
- **Shot matching** — Find visually similar shots across the video
- **Custom prompts** — Ask the AI anything about your video
- **Thumbnail extraction** — Frame-accurate thumbnails via ffmpeg
- **YouTube URL support** — Paste a link, skip the upload
- **Side-by-side comparison** — Compare two videos with structured AI analysis
- **Export** — JSON, CSV, PDF, Markdown, EDL (CMX 3600), FCP XML
- **Real-time progress** — Server-Sent Events stream results as they're generated
- **BYOK** — Bring your own Google API key via the Settings menu

## Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 20+**
- **ffmpeg** (for thumbnail extraction)

### 1. Clone and install

```bash
git clone https://github.com/ijduncan/video-analyzer.git
cd video-analyzer

# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

### 2. Run

```bash
# Terminal 1 — Backend
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm run dev
```

Or use the convenience script:

```bash
./scripts/dev.sh
```

Open **http://localhost:5173**

### 3. Set your API key

Click the gear icon in the top-right corner and enter your [Google AI Studio API key](https://aistudio.google.com/apikey). The key is stored in your browser's localStorage and sent directly to Google's API — it never touches any other server.

Alternatively, create a `.env` file in the project root:

```
GOOGLE_API_KEY=your-key-here
```

## Docker

Run everything with one command:

```bash
docker compose up --build
```

Open **http://localhost:5173**

## Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | React 19, Vite 7, Tailwind CSS v4, Zustand |
| Backend | Python, FastAPI, SSE (sse-starlette) |
| AI | Google Gemini 2.5 Flash + Pro (google-genai SDK) |
| Video | ffmpeg (thumbnails), Google File API (upload) |

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` | Play / Pause |
| `Left` / `Right` | Seek -5s / +5s |
| `1`-`6` | Switch tabs (Timeline, Detail, Summary, Matches, Custom, Raw) |

## License

MIT
