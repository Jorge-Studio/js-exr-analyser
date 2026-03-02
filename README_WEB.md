# EXR Analyzer — Web App

React + TypeScript frontend (Material 3–style UI) and Python FastAPI backend. Same color scheme as the desktop app; responsive layout.

## Run locally

### Backend (Python)

```bash
cd /path/to/js-exr-analyser
python -m venv venv  # if not already
source venv/bin/activate   # or venv\Scripts\activate on Windows
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (Node)

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). The Vite dev server proxies `/api` to the backend (port 8000).

## Build for production

```bash
cd frontend && npm run build
```

Serve the `frontend/dist` folder with any static server and point the app to your API (e.g. set `VITE_API_URL` or proxy `/api` to the backend).

## Tabs

- **Organizer** — Placeholder (folder scan can be added).
- **Analyzer** — Upload EXR or video (MOV, MP4, etc.); view metadata, bit depth, quality.
- **Sequence** — Placeholder (EXR sequence playback/export).
- **Shots** — List of subsections from feedback PDF; notes per shot; video upload/compare can be extended here.

## Design

- **Material 3**–inspired: rounded corners (12px), tonal surfaces, same dark palette as desktop (`#0D0D0D`, `#00FF88` accent).
- **Responsive**: drawer collapses to hamburger on small screens; grid stacks on mobile.
