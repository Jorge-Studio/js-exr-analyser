"""
EXR Analyzer — Web API (Python backend).
Run: uvicorn backend.main:app --reload
"""
import os

os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"

import base64
import glob
import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.analysis import analyze_exr, analyze_video, _tonemap_preview
from backend.shots_data import SHOTS_DATA

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

app = FastAPI(title="EXR Analyzer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# ── Shots ────────────────────────────────────────────────────────────

@app.get("/api/shots")
def get_shots():
    return {"shots": SHOTS_DATA}


# ── Analyzer ─────────────────────────────────────────────────────────

@app.post("/api/analyze-exr")
async def api_analyze_exr(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".exr"):
        raise HTTPException(400, "EXR file required")
    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    try:
        result = analyze_exr(tmp_path)
        result["filename"] = file.filename or result["filename"]
        return result
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


@app.post("/api/analyze-video")
async def api_analyze_video(file: UploadFile = File(...)):
    ext = (Path(file.filename or "").suffix or "").lower()
    if ext not in (".mov", ".mp4", ".avi", ".mkv", ".mxf", ".webm", ".m4v", ".mpg", ".mpeg"):
        raise HTTPException(400, "Video file required (MOV, MP4, etc.)")
    suffix = Path(file.filename or "video").suffix or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    try:
        result = analyze_video(tmp_path)
        result["filename"] = file.filename or result["filename"]
        return result
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# ── Organizer (extract frames from video) ────────────────────────────

@app.post("/api/extract-frames")
async def api_extract_frames(
    file: UploadFile = File(...),
    format: str = Form("png"),
):
    """Extract all frames from a video. Returns a ZIP of extracted frames."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise HTTPException(500, "FFmpeg is not installed on the server.")
    ext = (Path(file.filename or "").suffix or "").lower()
    if ext not in (".mov", ".mp4", ".avi", ".mkv", ".mxf", ".webm", ".m4v", ".mpg", ".mpeg"):
        raise HTTPException(400, "Video file required")
    suffix = Path(file.filename or "video").suffix or ".mp4"
    work_dir = tempfile.mkdtemp()
    video_path = os.path.join(work_dir, f"input{suffix}")
    try:
        content = await file.read()
        with open(video_path, "wb") as f:
            f.write(content)
        out_ext = "exr" if format.lower() == "exr" else "png"
        out_pattern = os.path.join(work_dir, f"frame_%06d.{out_ext}")
        pix_fmt = "rgb48le" if out_ext == "exr" else "rgb24"
        cmd = [ffmpeg, "-i", video_path, "-pix_fmt", pix_fmt, out_pattern, "-y"]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if proc.returncode != 0:
            raise HTTPException(500, f"FFmpeg error: {proc.stderr[-500:]}")
        frames = sorted(glob.glob(os.path.join(work_dir, f"frame_*.{out_ext}")))
        if not frames:
            raise HTTPException(500, "No frames extracted")
        zip_path = os.path.join(work_dir, "frames.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for fp in frames:
                zf.write(fp, os.path.basename(fp))
        base_name = Path(file.filename or "video").stem
        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename=f"{base_name}_frames.zip",
            background=None,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# ── Sequence (serve EXR frames for playback) ─────────────────────────

_sequence_store: dict = {}


@app.post("/api/sequence/upload")
async def api_sequence_upload(files: list[UploadFile] = File(...)):
    """Upload multiple EXR files for sequence playback."""
    if not cv2 or not np:
        raise HTTPException(500, "OpenCV not available")
    work_dir = tempfile.mkdtemp()
    frame_paths = []
    for f in files:
        safe_name = Path(f.filename or "frame.exr").name
        dest = os.path.join(work_dir, safe_name)
        content = await f.read()
        with open(dest, "wb") as fp:
            fp.write(content)
        frame_paths.append(dest)
    frame_paths.sort()
    session_id = os.path.basename(work_dir)
    _sequence_store[session_id] = {
        "dir": work_dir,
        "frames": frame_paths,
        "count": len(frame_paths),
    }
    return {
        "session_id": session_id,
        "frame_count": len(frame_paths),
        "filenames": [os.path.basename(p) for p in frame_paths],
    }


@app.get("/api/sequence/{session_id}/frame/{index}")
def api_sequence_frame(
    session_id: str,
    index: int,
    exposure: float = 0.0,
    gamma: float = 1.0,
):
    """Return a single frame as base64 JPEG with optional exposure/gamma."""
    session = _sequence_store.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found. Upload frames first.")
    if index < 0 or index >= session["count"]:
        raise HTTPException(400, f"Frame index out of range (0–{session['count']-1})")
    path = session["frames"][index]
    img = cv2.imread(path, cv2.IMREAD_ANYDEPTH | cv2.IMREAD_ANYCOLOR)
    if img is None:
        raise HTTPException(500, f"Could not read frame {index}")
    if img.dtype != np.float32:
        img = img.astype(np.float32) / (np.iinfo(img.dtype).max if img.dtype.kind in "ui" else 255.0)
    if img.ndim == 2:
        img = np.stack([img, img, img], axis=-1)
    elif img.shape[2] > 3:
        img = img[:, :, :3]
    img_rgb = np.ascontiguousarray(img[:, :, ::-1], dtype=np.float32)
    if exposure != 0.0:
        img_rgb = img_rgb * (2.0 ** exposure)
    preview_b64 = _tonemap_preview(img_rgb, gamma=gamma)
    return {
        "frame": index,
        "filename": os.path.basename(path),
        "width": img.shape[1],
        "height": img.shape[0],
        "preview_b64": preview_b64,
    }


@app.delete("/api/sequence/{session_id}")
def api_sequence_delete(session_id: str):
    session = _sequence_store.pop(session_id, None)
    if session:
        shutil.rmtree(session["dir"], ignore_errors=True)
    return {"status": "ok"}
