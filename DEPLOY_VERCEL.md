# Deploy EXR Analyzer as a Web App on Vercel

You can run the same EXR/video upload, compare, and analysis in the browser by deploying the **frontend** to Vercel and the **Python backend** to a host that runs 24/7 (e.g. Railway or Render). Vercel is optimized for the React app; the backend needs a Python runtime with OpenCV/NumPy for full EXR and video support.

---

## 1. Deploy frontend to Vercel

1. Push this repo to GitHub (if you haven’t already).
2. Go to [vercel.com](https://vercel.com) → **Add New Project** → import your repo.
3. Set **Root Directory** to **`frontend`** (so Vercel builds the React app).
4. Leave **Build Command** as `npm run build` and **Output Directory** as `dist`.
5. (Optional) Add environment variable:
   - **Name:** `VITE_API_URL`  
   - **Value:** your backend URL, e.g. `https://your-app-name.railway.app`  
   Do **not** add a trailing slash.  
   If you skip this, the app will still build and run, but “Analyzer” and “Shots” will only work once the backend is deployed and you add this variable.
6. Deploy. Your app will be at `https://your-project.vercel.app`.

The app will:
- Serve the same UI (Organizer, Analyzer, Sequence, Shots).
- Call the backend at `VITE_API_URL` for upload/analyze and shots data when that env var is set.

---

## 2. Deploy backend (for upload, analyze, and full EXR/video capabilities)

The backend is the `backend/` folder (FastAPI + OpenCV + NumPy). It must run on a service that supports Python and long-running or request-based processes (not only serverless). Two simple options:

### Option A: Railway

1. Go to [railway.app](https://railway.app) and sign in with GitHub.
2. **New Project** → **Deploy from GitHub repo** → select this repo.
3. Leave **Root Directory** at the repo root. Configure:
   - **Build command:** `pip install -r backend/requirements.txt`
   - **Start command:** `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
4. Add a **Public URL** (e.g. `https://your-app-name.railway.app`).
5. Copy that URL into Vercel’s **`VITE_API_URL`** (no trailing slash).

### Option B: Render

1. Go to [render.com](https://render.com) → **New** → **Web Service**.
2. Connect this repo and set:
   - **Root Directory:** (repo root)
   - **Build:** `pip install -r backend/requirements.txt`
   - **Start:** `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
3. Create the service and copy the URL (e.g. `https://your-app-name.onrender.com`).
4. Set **`VITE_API_URL`** in Vercel to that URL (no trailing slash).

**CORS:** The backend in this repo allows origins like `https://*.vercel.app`. If you use a custom domain on Vercel, add it to the `allow_origins` list in `backend/main.py` (see the `CORSMiddleware` block).

---

## 3. What works after deploy

- **Organizer / Sequence:** UI is there; backend endpoints for these can be added later if needed.
- **Analyzer:** Users can upload EXR or video (MOV, MP4, etc.) and get the same info as the desktop app (metadata, bit depth, quality, etc.) as long as `VITE_API_URL` points to the deployed backend.
- **Shots:** The shots list and notes are loaded from the backend; again, `VITE_API_URL` must be set.

So: **frontend on Vercel + backend on Railway (or Render)** gives you a web app you can deploy on Vercel that still allows upload, compare, and full EXR/video analysis.

---

## 4. Backend running locally (no backend deploy)

For local testing without deploying the backend:

- In the repo root: `venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000`
- In `frontend`: `npm run dev` (Vite proxies `/api` to port 8000).
- Do **not** set `VITE_API_URL`; the proxy handles API calls.
