"""
EXR Analyzer — Vercel Serverless API.
Uses OpenEXR + Pillow (lightweight, no OpenCV needed).
"""
import base64
import io
import math
import os
import tempfile
from pathlib import Path

import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

try:
    import OpenEXR
    import Imath
    _EXR_AVAILABLE = True
except ImportError:
    _EXR_AVAILABLE = False

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Shots data ───────────────────────────────────────────────────────

SHOTS_DATA = [
    {"id": "GA1020", "label": "GA1020", "time_range": "00:00\u20131:04", "notes": "Both GA shots are cutaways in the commercial. Match roughly using our train; train can move faster, not slower. Beauty shots: no overcast, no excessive atmosphere, no city backdrop."},
    {"id": "GA1100", "label": "GA1100", "time_range": "1:15\u20132:25", "notes": "No unattractive trailers/cars on floor. Focus on train in beautiful environment (especially crossing bridge). Train must not appear electric."},
    {"id": "CC1540", "label": "CC1540", "time_range": "2:41\u20134:14", "notes": "Train approaching haunted area; they like the atmosphere. Do not use full length of stock. Start with engine + eight cars; keep consistent."},
    {"id": "CC1920", "label": "CC1920", "time_range": "4:22\u20135:09", "notes": "Train moving too slowly\u2014should be faster. Approach to haunted tunnel; atmosphere and ambiance work well."},
    {"id": "CC1920_2", "label": "CC1920 (2)", "time_range": "5:09\u20136:08", "notes": "Switch shot: train approaching switch, then arriving by switch when it completes. Emphasize switch action at last moment."},
    {"id": "MT1420", "label": "MT1420", "time_range": "6:24\u20137:08", "notes": "Wheel slightly comes off track, sparks. Match what\u2019s here best you can."},
    {"id": "CF4240", "label": "CF4240", "time_range": "7:47\u20139:40", "notes": "Keep falling character as separate element for future feedback. Equal effort on environment and train for approvals."},
    {"id": "CF1000", "label": "CF1000", "time_range": "9:41\u201311:25", "notes": "BG from still of stock doesn\u2019t work. New angle looking down ravine for depth. Prioritize wider/deeper environment over fall position."},
    {"id": "CF4240_plate", "label": "CF4240 (plate depth)", "time_range": "11:31\u201312:30", "notes": "Make depth below train twice as deep for this plate."},
    {"id": "SC1600", "label": "SC1600", "time_range": "13:03\u201316:28", "notes": "Calm then train enters rapidly approaching storm. Lightning strikes train\u2014two bolts. Beginning of storm\u2014not extreme weather yet."},
    {"id": "VT1000", "label": "VT1000", "time_range": "17:07\u201319:44", "notes": "Same storm as SC1600; consistency in atmosphere and lighting. Different camera angle for train-hit-by-lightning."},
    {"id": "BT1820", "label": "BT1820", "time_range": "28:48\u201329:53", "notes": "Underwater storm environment; joke about excessive rainfall. Blowfish as separate element."},
]

# ── Analysis helpers ─────────────────────────────────────────────────

def _tonemap_preview(img: np.ndarray, gamma: float = 2.2) -> str:
    """Reinhard tonemap -> JPEG base64 via Pillow."""
    display = np.clip(img.astype(np.float64), 0, None)
    display = display / (1.0 + display)
    display = np.power(np.clip(display, 0, 1), 1.0 / max(gamma, 0.1))
    display = (display * 255).astype(np.uint8)
    pil_img = Image.fromarray(display, "RGB")
    buf = io.BytesIO()
    pil_img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _compute_waveform(img: np.ndarray, num_cols: int = 256) -> dict:
    h, w, _ = img.shape
    step = max(1, w // num_cols)
    cols = list(range(0, w, step))
    waveform: dict = {"positions": [], "R": [], "G": [], "B": []}
    for col_idx in cols:
        col_end = min(col_idx + step, w)
        waveform["positions"].append(round(col_idx * 0.001, 4))
        for i, ch in enumerate(["R", "G", "B"]):
            col_data = img[:, col_idx:col_end, i].flatten()
            finite = col_data[np.isfinite(col_data)]
            if finite.size == 0:
                waveform[ch].append({"min": 0, "max": 0, "mean": 0})
            else:
                waveform[ch].append({
                    "min": round(float(np.min(finite)), 4),
                    "max": round(float(np.max(finite)), 4),
                    "mean": round(float(np.mean(finite)), 4),
                })
    return waveform


def _compute_histogram(img: np.ndarray, n_bins: int = 256) -> dict:
    bin_edges = np.linspace(-0.1, 2.0, n_bins + 1)
    centers = [round(float(x), 4) for x in 0.5 * (bin_edges[:-1] + bin_edges[1:])]
    histogram: dict = {"bin_centers": centers}
    for i, ch in enumerate(["R", "G", "B"]):
        data = img[:, :, i].flatten()
        clipped = np.clip(data, -0.1, 2.0)
        counts, _ = np.histogram(clipped, bins=bin_edges, density=False)
        density = counts / (clipped.size * (bin_edges[1] - bin_edges[0]))
        histogram[ch] = [round(float(d), 4) for d in density]
    return histogram


def _detect_encoding(means, maxes):
    avg_mean, avg_max = np.mean(means), np.mean(maxes)
    if avg_max > 5.0 and avg_mean < 2.0:
        return "Linear (scene-referred)"
    if avg_max < 1.5 and avg_mean > 0.15:
        return "Log (ACEScct/LogC)"
    if avg_max < 1.1:
        return "Linear (SDR)"
    if avg_max > 1.5:
        return "Linear (scene-referred)"
    return "Unknown"


def _analyze_image(img: np.ndarray, filepath: str, extra_meta: dict | None = None) -> dict:
    height, width = img.shape[:2]
    channels = ["R", "G", "B"]
    results = {}
    means, maxes = [], []
    for i, ch in enumerate(channels):
        arr = img[:, :, i].flatten()
        finite = arr[np.isfinite(arr)]
        if finite.size == 0:
            finite = np.array([0.0], dtype=np.float32)
        unique = np.unique(finite)
        midtone = unique[(unique > 0.2) & (unique < 0.5)]
        step_ratio = 0.0
        if len(midtone) > 1:
            diffs = np.diff(midtone.astype(np.float64))
            step_ratio = (1.0 / 255) / diffs.mean() if diffs.mean() > 0 else 0
        results[ch] = {
            "unique_count": int(len(unique)),
            "min": round(float(np.min(finite)), 4),
            "max": round(float(np.max(finite)), 4),
            "mean": round(float(np.mean(finite)), 4),
            "step_ratio": round(float(step_ratio), 2),
        }
        means.append(results[ch]["mean"])
        maxes.append(results[ch]["max"])
    avg_unique = float(np.mean([results[c]["unique_count"] for c in channels]))
    eff_bits = math.log2(avg_unique) if avg_unique > 1 else 0
    above_1 = 100 * float(np.sum(img.flatten() > 1.0)) / max(img.size, 1)
    if eff_bits >= 13.0: rating = "\u2605\u2605\u2605\u2605\u2605 Cinema-grade"
    elif eff_bits >= 11.5: rating = "\u2605\u2605\u2605\u2605\u2606 Good"
    elif eff_bits >= 10.0: rating = "\u2605\u2605\u2605\u2606\u2606 Acceptable"
    elif eff_bits >= 8.5: rating = "\u2605\u2605\u2606\u2606\u2606 Poor"
    else: rating = "\u2605\u2606\u2606\u2606\u2606 8-bit equivalent"
    fsize = os.path.getsize(filepath)
    result = {
        "filename": os.path.basename(filepath),
        "width": width, "height": height,
        "filesize": fsize, "filesize_mb": round(fsize / 1024 / 1024, 2),
        "eff_bits": round(eff_bits, 2), "avg_unique": round(avg_unique, 2),
        "above_1_pct": round(above_1, 2), "rating": rating, "results": results,
        "avg_step_ratio": round(float(np.mean([results[c]["step_ratio"] for c in channels])), 2),
        "range_min": round(float(min(results[c]["min"] for c in channels)), 4),
        "range_max": round(float(max(results[c]["max"] for c in channels)), 4),
        "encoding": _detect_encoding(means, maxes),
        "preview_b64": _tonemap_preview(img),
        "waveform": _compute_waveform(img),
        "histogram": _compute_histogram(img),
    }
    if extra_meta:
        result.update(extra_meta)
    return result


def _read_exr(filepath: str) -> np.ndarray:
    """Read EXR using OpenEXR library (no OpenCV needed)."""
    if not _EXR_AVAILABLE:
        raise RuntimeError("OpenEXR library not available")
    exr_file = OpenEXR.InputFile(filepath)
    header = exr_file.header()
    dw = header["dataWindow"]
    width = dw.max.x - dw.min.x + 1
    height = dw.max.y - dw.min.y + 1
    pt = Imath.PixelType(Imath.PixelType.FLOAT)
    available = list(header.get("channels", {}).keys())
    r_name = "R" if "R" in available else available[0] if available else "R"
    g_name = "G" if "G" in available else r_name
    b_name = "B" if "B" in available else r_name
    r_str = exr_file.channel(r_name, pt)
    g_str = exr_file.channel(g_name, pt)
    b_str = exr_file.channel(b_name, pt)
    r = np.frombuffer(r_str, dtype=np.float32).reshape(height, width)
    g = np.frombuffer(g_str, dtype=np.float32).reshape(height, width)
    b = np.frombuffer(b_str, dtype=np.float32).reshape(height, width)
    return np.stack([r, g, b], axis=-1).astype(np.float32)


def _read_image_pillow(filepath: str) -> np.ndarray:
    """Read non-EXR image via Pillow, return float32 RGB array."""
    pil = Image.open(filepath).convert("RGB")
    arr = np.array(pil, dtype=np.float32) / 255.0
    return arr


# ── API Routes ───────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/shots")
def get_shots():
    return {"shots": SHOTS_DATA}


@app.post("/api/analyze-exr")
async def api_analyze_exr(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".exr"):
        raise HTTPException(400, "EXR file required")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".exr") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    try:
        img = _read_exr(tmp_path)
        result = _analyze_image(img, tmp_path, {
            "compression": "EXR",
            "native_type": "32-bit float",
            "colorspace": "Linear / Unknown",
        })
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
    allowed = {".mov", ".mp4", ".avi", ".mkv", ".mxf", ".webm", ".m4v", ".mpg", ".mpeg",
               ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
    if ext not in allowed:
        raise HTTPException(400, "Supported: video or image files")
    suffix = Path(file.filename or "file").suffix or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    try:
        img = _read_image_pillow(tmp_path)
        result = _analyze_image(img, tmp_path, {
            "compression": ext.lstrip(".").upper(),
            "native_type": "8-bit",
            "colorspace": "sRGB",
        })
        result["filename"] = file.filename or result["filename"]
        return result
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
