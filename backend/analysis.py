"""
Standalone analysis for web API: EXR and video.
Returns JSON-serializable dicts including visualization data (preview, waveform, histogram).
"""
import base64
import io
import json
import math
import os
import shutil
import subprocess

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None


def _find_ffprobe():
    return shutil.which("ffprobe")


def _parse_fps(r_frame_rate):
    if not r_frame_rate:
        return 24.0
    try:
        parts = str(r_frame_rate).split("/")
        if len(parts) == 2:
            num, den = float(parts[0]), float(parts[1])
            return num / den if den else 24.0
        return float(r_frame_rate)
    except (ValueError, ZeroDivisionError):
        return 24.0


def _pix_fmt_to_bit_depth(pix_fmt):
    if not pix_fmt:
        return 8
    p = str(pix_fmt).lower()
    if "12" in p:
        return 12
    if "10" in p:
        return 10
    if "16" in p:
        return 16
    return 8


def probe_video(filepath: str) -> dict | None:
    ffprobe = _find_ffprobe()
    if not ffprobe:
        return None
    try:
        cmd = [ffprobe, "-v", "quiet", "-show_format", "-show_streams", "-print_format", "json", filepath]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if proc.returncode != 0:
            return None
        data = json.loads(proc.stdout or "{}")
        for s in data.get("streams", []):
            if s.get("codec_type") == "video":
                fps = _parse_fps(s.get("r_frame_rate"))
                pix_fmt = s.get("pix_fmt", "")
                duration = float(s.get("duration") or data.get("format", {}).get("duration") or 0)
                nb_frames = s.get("nb_frames")
                if nb_frames is not None:
                    try:
                        nb_frames = int(nb_frames)
                    except (ValueError, TypeError):
                        nb_frames = None
                return {
                    "fps": fps,
                    "bit_depth": _pix_fmt_to_bit_depth(pix_fmt),
                    "width": int(s.get("width", 0)),
                    "height": int(s.get("height", 0)),
                    "codec_name": s.get("codec_name", ""),
                    "pix_fmt": pix_fmt,
                    "duration": duration,
                    "nb_frames": nb_frames,
                    "profile": s.get("profile", ""),
                }
        return None
    except Exception:
        return None


def _tonemap_preview(img: np.ndarray, gamma: float = 2.2) -> str:
    """Reinhard + gamma tonemap, encode as base64 JPEG."""
    display = np.clip(img.astype(np.float64), 0, None)
    display = display / (1.0 + display)
    display = np.power(np.clip(display, 0, 1), 1.0 / max(gamma, 0.1))
    display = (display * 255).astype(np.uint8)
    display_bgr = cv2.cvtColor(display, cv2.COLOR_RGB2BGR)
    _, buf = cv2.imencode(".jpg", display_bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return base64.b64encode(buf).decode("ascii")


def _compute_waveform(img: np.ndarray, num_cols: int = 256) -> dict:
    """Compute per-column min/mean/max for each channel (envelope waveform)."""
    h, w, _ = img.shape
    step = max(1, w // num_cols)
    cols = list(range(0, w, step))
    waveform = {"positions": [], "R": [], "G": [], "B": []}
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
    """Compute histogram bins for each RGB channel."""
    bin_edges = np.linspace(-0.1, 2.0, n_bins + 1)
    centers = [round(float(x), 4) for x in 0.5 * (bin_edges[:-1] + bin_edges[1:])]
    histogram = {"bin_centers": centers}
    for i, ch in enumerate(["R", "G", "B"]):
        data = img[:, :, i].flatten()
        data_clipped = np.clip(data, -0.1, 2.0)
        counts, _ = np.histogram(data_clipped, bins=bin_edges, density=False)
        density = counts / (data_clipped.size * (bin_edges[1] - bin_edges[0]))
        histogram[ch] = [round(float(d), 4) for d in density]
    return histogram


def _detect_encoding(means, maxes):
    avg_mean = np.mean(means)
    avg_max = np.mean(maxes)
    if avg_max > 5.0 and avg_mean < 2.0:
        return "Linear (scene-referred)"
    elif avg_max < 1.5 and avg_mean > 0.15:
        return "Log (ACEScct/LogC)"
    elif avg_max < 1.1:
        return "Linear (SDR)"
    elif avg_max > 1.5:
        return "Linear (scene-referred)"
    return "Unknown"


def _analyze_image(img: np.ndarray, filepath: str, extra_meta: dict | None = None) -> dict:
    """Common analysis for both EXR and video frames."""
    height, width = img.shape[:2]
    rgb_channels = ["R", "G", "B"]
    results = {}
    means, maxes = [], []
    for i, ch in enumerate(rgb_channels):
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
    avg_unique = float(np.mean([results[ch]["unique_count"] for ch in rgb_channels]))
    eff_bits = math.log2(avg_unique) if avg_unique > 1 else 0
    above_1 = 100 * float(np.sum(img.flatten() > 1.0)) / max(img.size, 1)
    if eff_bits >= 13.0:
        rating = "★★★★★ Cinema-grade"
    elif eff_bits >= 11.5:
        rating = "★★★★☆ Good"
    elif eff_bits >= 10.0:
        rating = "★★★☆☆ Acceptable"
    elif eff_bits >= 8.5:
        rating = "★★☆☆☆ Poor"
    else:
        rating = "★☆☆☆☆ 8-bit equivalent"
    fsize = os.path.getsize(filepath)
    encoding = _detect_encoding(means, maxes)
    preview_b64 = _tonemap_preview(img)
    waveform = _compute_waveform(img)
    histogram = _compute_histogram(img)
    result = {
        "filename": os.path.basename(filepath),
        "width": width,
        "height": height,
        "filesize": fsize,
        "filesize_mb": round(fsize / 1024 / 1024, 2),
        "eff_bits": round(eff_bits, 2),
        "avg_unique": round(avg_unique, 2),
        "above_1_pct": round(above_1, 2),
        "rating": rating,
        "results": results,
        "avg_step_ratio": round(float(np.mean([results[ch]["step_ratio"] for ch in rgb_channels])), 2),
        "range_min": round(float(min(results[ch]["min"] for ch in rgb_channels)), 4),
        "range_max": round(float(max(results[ch]["max"] for ch in rgb_channels)), 4),
        "encoding": encoding,
        "preview_b64": preview_b64,
        "waveform": waveform,
        "histogram": histogram,
    }
    if extra_meta:
        result.update(extra_meta)
    return result


def analyze_video(filepath: str) -> dict:
    probe = probe_video(filepath)
    if not probe:
        raise RuntimeError("Could not probe video. Install FFmpeg (ffprobe).")
    if not cv2:
        raise RuntimeError("OpenCV is required for video analysis.")
    cap = cv2.VideoCapture(filepath)
    if not cap.isOpened():
        raise RuntimeError("Could not open video.")
    try:
        ret, frame = cap.read()
        if not ret or frame is None:
            raise RuntimeError("Could not read first frame.")
        h, w = frame.shape[:2]
        if frame.dtype != np.float32 and frame.dtype != np.float64:
            img = frame.astype(np.float32) / (np.iinfo(frame.dtype).max if frame.dtype.kind in "ui" else 255.0)
        else:
            img = frame.astype(np.float32)
        if img.ndim == 2:
            img = np.stack([img, img, img], axis=-1)
        elif img.shape[2] == 1:
            img = np.repeat(img, 3, axis=2)
        else:
            img = img[:, :, :3].copy()
        img = np.ascontiguousarray(img[:, :, ::-1], dtype=np.float32)
    finally:
        cap.release()
    nb = probe.get("nb_frames")
    if nb is None and probe.get("duration") and probe.get("fps"):
        nb = int(probe["duration"] * probe["fps"])
    extra = {
        "compression": probe.get("codec_name", "Unknown"),
        "native_type": f"{probe['bit_depth']}-bit ({probe.get('pix_fmt', '')})",
        "colorspace": "Video",
        "fps": probe.get("fps"),
        "duration": probe.get("duration", 0),
        "nb_frames": nb,
        "video_metadata": probe,
    }
    return _analyze_image(img, filepath, extra)


def analyze_exr(filepath: str) -> dict:
    if not cv2:
        raise RuntimeError("OpenCV is required for EXR analysis.")
    img = cv2.imread(filepath, cv2.IMREAD_ANYDEPTH | cv2.IMREAD_ANYCOLOR)
    if img is None:
        raise RuntimeError("Could not read EXR.")
    if img.dtype != np.float32 and img.dtype != np.float64:
        img = img.astype(np.float32) / (np.iinfo(img.dtype).max if img.dtype.kind in "ui" else 255.0)
    else:
        img = img.astype(np.float32)
    height, width = img.shape[:2]
    if img.ndim == 2:
        img = np.stack([img, img, img], axis=-1)
    elif img.shape[2] == 1:
        img = np.repeat(img, 3, axis=2)
    else:
        img = img[:, :, :3].copy()
    img = np.ascontiguousarray(img[:, :, ::-1], dtype=np.float32)
    extra = {
        "compression": "Unknown (OpenCV)",
        "native_type": "32-bit float",
        "colorspace": "Unknown (OpenCV)",
    }
    return _analyze_image(img, filepath, extra)
