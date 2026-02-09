"""
EXR Viewer & Analyzer — Cinema VFX Pipeline Diagnostic Tool
A visual GUI for analyzing EXR bit depth, waveform, and quality metrics.

Usage:
    python exr_analyzer.py
    python exr_analyzer.py <file.exr>
"""

import sys
import os
import re
import subprocess
import traceback

# Version (single source of truth: VERSION file)
_ROOT = os.path.dirname(os.path.abspath(__file__))
def _get_version():
    vpath = os.path.join(_ROOT, "VERSION")
    if os.path.isfile(vpath):
        try:
            with open(vpath, encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass
    return "0.0.0"
__version__ = _get_version()

# Python version check (required 3.8+)
def _show_error_win(msg, title="EXR Analyzer - Error"):
    """Show error in a message box on Windows so the window doesn't close silently."""
    if sys.platform == "win32":
        try:
            import ctypes
            # Write crash log so user can send it even if message box is truncated
            try:
                log_path = os.path.join(_ROOT, "exr_analyzer_crash.log")
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write(title + "\n\n" + msg)
            except Exception:
                pass
            ctypes.windll.user32.MessageBoxW(0, msg, title, 0x10)
            return
        except Exception:
            pass
    print(title + "\n" + msg)


def _windows_excepthook(exc_type, exc_value, exc_tb):
    """On Windows, show any uncaught exception in a message box so the app doesn't close silently."""
    if sys.platform != "win32":
        return
    msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    try:
        log_path = os.path.join(_ROOT, "exr_analyzer_crash.log")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(msg)
    except Exception:
        pass
    _show_error_win(
        "An unexpected error occurred:\n\n" + msg[:2000] + ("\n\n... (see exr_analyzer_crash.log for full trace)" if len(msg) > 2000 else ""),
        "EXR Analyzer - Error",
    )
    # Call default to still print to stderr if there is a console
    if hasattr(sys, "__excepthook__") and sys.__excepthook__ is not _windows_excepthook:
        sys.__excepthook__(exc_type, exc_value, exc_tb)


if sys.platform == "win32":
    sys.excepthook = _windows_excepthook

if sys.version_info < (3, 8):
    _show_error_win(
        "Python 3.8 or newer is required.\n\n"
        "Current: " + sys.version.split()[0] + "\n\n"
        "Please install Python 3.8+ from https://www.python.org/downloads/\n"
        "On Windows, check 'Add Python to PATH' during installation."
    )
    sys.exit(1)

# Install requirements; on Windows try core-only first so numpy etc. install even if OpenEXR fails
def _install_requirements():
    root = os.path.dirname(os.path.abspath(__file__))
    if sys.platform == "win32":
        core_file = os.path.join(root, "requirements-core.txt")
        if os.path.isfile(core_file):
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-q", "-r", core_file],
                    cwd=root,
                    check=False,
                    timeout=180,
                    capture_output=True,
                )
            except Exception:
                pass
    req_file = os.path.join(root, "requirements.txt")
    if not os.path.isfile(req_file):
        return True
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "-r", req_file],
            cwd=root,
            check=False,
            timeout=180,
            capture_output=True,
        )
    except Exception:
        pass
    return True

_install_requirements()

try:
    import math
    import numpy as np
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem,
        QSplitter, QFrame, QScrollArea, QGroupBox, QGridLayout, QComboBox,
        QProgressBar, QSizePolicy, QDialog, QToolBar, QSlider, QSpinBox,
        QCheckBox, QTabWidget, QStackedWidget, QProgressDialog, QMessageBox, QDoubleSpinBox,
    )
    from PyQt5.QtCore import Qt, QSize, pyqtSignal, QTimer, QThread
    from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QFont, QPen, QCursor
    import pyqtgraph as pg
    USE_OPENEXR = False
    try:
        import OpenEXR
        import Imath
        USE_OPENEXR = True
    except ImportError:
        os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"
        import cv2
    import matplotlib
    matplotlib.use('Qt5Agg')
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
    from matplotlib.figure import Figure
except Exception as _import_err:
    _show_error_win(
        "Failed to load dependencies:\n\n" + str(_import_err) + "\n\n"
        "Install from a terminal (in this folder):\n"
        "  pip install -r requirements.txt\n\n"
        "Python: " + sys.version.split()[0] + "\n"
        "Required: Python 3.8+",
        "EXR Analyzer - Error",
    )
    sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════════
# COLOR SCHEME
# ══════════════════════════════════════════════════════════════════════════════

COLORS = {
    'bg': '#0D0D0D',
    'bg_light': '#1A1A1A',
    'bg_card': '#141414',
    'text': '#E8E8E8',
    'text_dim': '#888888',
    'accent': '#00FF88',
    'warning': '#FFaa00',
    'error': '#FF4444',
    'red': '#FF6B6B',
    'green': '#4ECB71',
    'blue': '#4A90D9',
    'border': '#333333',
}

STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {COLORS['bg']};
    color: {COLORS['text']};
    font-family: 'SF Pro Display', 'Segoe UI', 'Helvetica Neue', sans-serif;
}}
QLabel {{
    color: {COLORS['text']};
}}
QPushButton {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    padding: 8px 16px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: {COLORS['border']};
    border-color: {COLORS['accent']};
}}
QPushButton:pressed {{
    background-color: {COLORS['accent']};
    color: {COLORS['bg']};
}}
QPushButton#fullscreen_btn {{
    padding: 4px 8px;
    font-size: 14px;
    min-width: 30px;
}}
QTableWidget {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    gridline-color: {COLORS['border']};
    border-radius: 8px;
}}
QTableWidget::item {{
    padding: 8px;
    border-bottom: 1px solid {COLORS['border']};
}}
QHeaderView::section {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['text_dim']};
    padding: 8px;
    border: none;
    border-bottom: 1px solid {COLORS['border']};
    font-weight: 600;
    text-transform: uppercase;
    font-size: 11px;
}}
QGroupBox {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    margin-top: 16px;
    padding-top: 16px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 4px 12px;
    color: {COLORS['text_dim']};
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
}}
QScrollArea {{
    border: none;
    background-color: transparent;
}}
QDialog {{
    background-color: {COLORS['bg']};
}}
QToolBar {{
    background-color: {COLORS['bg_light']};
    border: none;
    spacing: 5px;
    padding: 5px;
}}
QSlider::groove:horizontal {{
    border: 1px solid {COLORS['border']};
    height: 6px;
    background: {COLORS['bg_light']};
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {COLORS['accent']};
    border: none;
    width: 14px;
    margin: -4px 0;
    border-radius: 7px;
}}
QSpinBox {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    padding: 4px;
    border-radius: 4px;
}}
"""


# ══════════════════════════════════════════════════════════════════════════════
# EXR ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

KNOWN_CHROMATICITIES = {
    "ACES AP0": ((0.7347, 0.2653), (0.0, 1.0), (0.0001, -0.077), (0.3217, 0.3377)),
    "ACES AP1 (ACEScg)": ((0.713, 0.293), (0.165, 0.830), (0.128, 0.044), (0.3217, 0.3377)),
    "Rec.709 / sRGB": ((0.64, 0.33), (0.30, 0.60), (0.15, 0.06), (0.3127, 0.3290)),
    "Rec.2020": ((0.708, 0.292), (0.170, 0.797), (0.131, 0.046), (0.3127, 0.3290)),
    "DCI-P3": ((0.680, 0.320), (0.265, 0.690), (0.150, 0.060), (0.3140, 0.3510)),
}


def identify_colorspace(chrom):
    if chrom is None:
        return "Unknown"
    try:
        r = (chrom.red.x, chrom.red.y)
        g = (chrom.green.x, chrom.green.y)
        b = (chrom.blue.x, chrom.blue.y)
        w = (chrom.white.x, chrom.white.y)
        file_chrom = (r, g, b, w)
    except AttributeError:
        return "Unknown"
    
    best_match, best_dist = "Unknown", float('inf')
    for name, ref in KNOWN_CHROMATICITIES.items():
        dist = sum(abs(float(fv) - float(rv)) for fc, rc in zip(file_chrom, ref) for fv, rv in zip(fc, rc))
        if dist < best_dist:
            best_dist, best_match = dist, name
    
    if best_dist < 0.05:
        return best_match
    elif best_dist < 0.15:
        return f"{best_match} (approx)"
    return "Unknown"


def detect_channel_type(header, channel_name):
    ch_info = header['channels'].get(channel_name)
    if ch_info is None:
        return None
    ptype = ch_info.type
    if ptype == Imath.PixelType(Imath.PixelType.HALF):
        return "HALF"
    elif ptype == Imath.PixelType(Imath.PixelType.FLOAT):
        return "FLOAT"
    return "UNKNOWN"


def read_channel(exr_file, header, channel_name):
    ch_type = detect_channel_type(header, channel_name)
    if ch_type == "FLOAT":
        pt = Imath.PixelType(Imath.PixelType.FLOAT)
        raw = exr_file.channel(channel_name, pt)
        arr = np.frombuffer(raw, dtype=np.float32)
        bit_label = "32-bit FLOAT"
    elif ch_type == "HALF":
        pt = Imath.PixelType(Imath.PixelType.HALF)
        raw = exr_file.channel(channel_name, pt)
        arr = np.frombuffer(raw, dtype=np.float16).astype(np.float32)
        bit_label = "16-bit HALF"
    else:
        pt = Imath.PixelType(Imath.PixelType.FLOAT)
        raw = exr_file.channel(channel_name, pt)
        arr = np.frombuffer(raw, dtype=np.float32)
        bit_label = f"{ch_type}"
    return arr, bit_label, ch_type


def detect_encoding(mean_vals, max_vals):
    avg_mean = np.mean(mean_vals)
    avg_max = np.mean(max_vals)
    if avg_max > 5.0 and avg_mean < 2.0:
        return "Linear (scene-referred)"
    elif avg_max < 1.5 and avg_mean > 0.15:
        return "Log (ACEScct/LogC)"
    elif avg_max < 1.1:
        return "Linear (SDR)"
    elif avg_max > 1.5:
        return "Linear (scene-referred)"
    return "Unknown"


def _analyze_exr_cv2(filepath):
    """Analyze EXR using OpenCV (fallback when OpenEXR is not installed, e.g. on Windows)."""
    img = cv2.imread(filepath, cv2.IMREAD_ANYDEPTH | cv2.IMREAD_ANYCOLOR)
    if img is None:
        raise RuntimeError("Could not read EXR with OpenCV. The file may be invalid or OpenCV was built without EXR support.")
    if img.dtype != np.float32 and img.dtype != np.float64:
        img = img.astype(np.float32) / (np.iinfo(img.dtype).max if img.dtype.kind in "ui" else 1.0)
    else:
        img = img.astype(np.float32)
    height, width = img.shape[:2]
    if img.ndim == 2:
        img = np.stack([img, img, img], axis=-1)
    elif img.shape[2] == 1:
        img = np.repeat(img, 3, axis=2)
    elif img.shape[2] >= 3:
        img = img[:, :, :3].copy()
    img = np.ascontiguousarray(img[:, :, ::-1], dtype=np.float32)
    rgb_channels = ['R', 'G', 'B']
    fsize = os.path.getsize(filepath)
    results = {}
    means, maxes = [], []
    for i, ch in enumerate(rgb_channels):
        arr = img[:, :, i].flatten()
        finite = arr[np.isfinite(arr)]
        if finite.size == 0:
            finite = np.array([0.0], dtype=np.float32)
        unique = np.unique(finite)
        midtone = unique[(unique > 0.2) & (unique < 0.5)]
        if len(midtone) > 1:
            diffs = np.diff(midtone.astype(np.float64))
            step_ratio = (1.0 / 255) / diffs.mean() if diffs.mean() > 0 else 0
        else:
            step_ratio = 0
        results[ch] = {
            'unique_count': len(unique),
            'bit_label': '32-bit float',
            'ch_type': 'FLOAT',
            'min': float(np.min(finite)),
            'max': float(np.max(finite)),
            'mean': float(np.mean(finite)),
            'step_ratio': step_ratio,
            'data': finite,
        }
        means.append(results[ch]['mean'])
        maxes.append(results[ch]['max'])
    encoding = detect_encoding(means, maxes)
    unique_counts = [results[ch]['unique_count'] for ch in rgb_channels]
    avg_unique = np.mean(unique_counts)
    eff_bits = math.log2(avg_unique) if avg_unique > 1 else 0
    all_vals = img.flatten()
    above_1 = 100 * np.sum(all_vals > 1.0) / max(len(all_vals), 1)
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
    avg_step_ratio = np.mean([results[ch]['step_ratio'] for ch in rgb_channels])
    return {
        'filepath': filepath,
        'filename': os.path.basename(filepath),
        'width': width,
        'height': height,
        'filesize': fsize,
        'filesize_mb': fsize / 1024 / 1024,
        'compression': 'Unknown (OpenCV)',
        'native_type': '32-bit float',
        'colorspace': 'Unknown (OpenCV)',
        'encoding': encoding,
        'eff_bits': eff_bits,
        'avg_unique': avg_unique,
        'above_1_pct': above_1,
        'rating': rating,
        'results': results,
        'img_data': img,
        'avg_step_ratio': avg_step_ratio,
        'range_min': min(results[ch]['min'] for ch in rgb_channels),
        'range_max': max(results[ch]['max'] for ch in rgb_channels),
    }


def analyze_exr(filepath):
    """Analyze an EXR file and return all metrics (uses OpenEXR or OpenCV fallback)."""
    if USE_OPENEXR:
        return _analyze_exr_openexr(filepath)
    return _analyze_exr_cv2(filepath)


def _analyze_exr_openexr(filepath):
    """Analyze an EXR file using the OpenEXR library (full metadata)."""
    f = OpenEXR.InputFile(filepath)
    header = f.header()
    dw = header['dataWindow']
    width = dw.max.x - dw.min.x + 1
    height = dw.max.y - dw.min.y + 1
    fsize = os.path.getsize(filepath)
    
    channels = sorted(header['channels'].keys())
    rgb_channels = [ch for ch in ['R', 'G', 'B'] if ch in channels]
    
    img_data = np.zeros((height, width, 3), dtype=np.float32)
    results = {}
    means, maxes = [], []
    
    for i, ch in enumerate(rgb_channels):
        arr, bit_label, ch_type = read_channel(f, header, ch)
        arr = arr.reshape((height, width))
        img_data[:, :, i] = arr
        
        finite = arr[np.isfinite(arr)].flatten()
        unique = np.unique(finite)
        
        midtone = unique[(unique > 0.2) & (unique < 0.5)]
        if len(midtone) > 1:
            diffs = np.diff(midtone.astype(np.float64))
            eight_bit_step = 1.0 / 255
            step_ratio = eight_bit_step / diffs.mean() if diffs.mean() > 0 else 0
        else:
            step_ratio = 0
        
        results[ch] = {
            'unique_count': len(unique),
            'bit_label': bit_label,
            'ch_type': ch_type,
            'min': float(finite.min()),
            'max': float(finite.max()),
            'mean': float(finite.mean()),
            'step_ratio': step_ratio,
            'data': finite,
        }
        means.append(finite.mean())
        maxes.append(finite.max())
    
    encoding = detect_encoding(means, maxes)
    chrom = header.get('chromaticities')
    colorspace = identify_colorspace(chrom)
    compression = str(header['compression']).replace('Compression.', '')
    
    unique_counts = [results[ch]['unique_count'] for ch in rgb_channels]
    avg_unique = np.mean(unique_counts)
    eff_bits = math.log2(avg_unique) if avg_unique > 1 else 0
    
    all_vals = img_data.flatten()
    above_1 = 100 * np.sum(all_vals > 1.0) / len(all_vals)
    
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
    
    ch_types = set(results[ch]['ch_type'] for ch in rgb_channels)
    native_type = "32-bit float" if "FLOAT" in ch_types else "16-bit half"
    avg_step_ratio = np.mean([results[ch]['step_ratio'] for ch in rgb_channels])
    
    return {
        'filepath': filepath,
        'filename': os.path.basename(filepath),
        'width': width,
        'height': height,
        'filesize': fsize,
        'filesize_mb': fsize / 1024 / 1024,
        'compression': compression,
        'native_type': native_type,
        'colorspace': colorspace,
        'encoding': encoding,
        'eff_bits': eff_bits,
        'avg_unique': avg_unique,
        'above_1_pct': above_1,
        'rating': rating,
        'results': results,
        'img_data': img_data,
        'avg_step_ratio': avg_step_ratio,
        'range_min': min(results[ch]['min'] for ch in rgb_channels),
        'range_max': max(results[ch]['max'] for ch in rgb_channels),
    }


def write_exr_frame(filepath, img_data):
    """Write RGB (H,W,3) or RGBA (H,W,4) float32 to an EXR file. Returns True on success."""
    if img_data is None or img_data.size == 0:
        return False
    try:
        h, w = img_data.shape[:2]
        has_alpha = img_data.shape[2] == 4
        if USE_OPENEXR:
            header = OpenEXR.Header(w, h)
            ch_dict = {
                "R": Imath.Channel(Imath.PixelType(Imath.PixelType.FLOAT)),
                "G": Imath.Channel(Imath.PixelType(Imath.PixelType.FLOAT)),
                "B": Imath.Channel(Imath.PixelType(Imath.PixelType.FLOAT)),
            }
            if has_alpha:
                ch_dict["A"] = Imath.Channel(Imath.PixelType(Imath.PixelType.FLOAT))
            header["channels"] = ch_dict
            out = OpenEXR.OutputFile(filepath, header)
            pix = {"R": img_data[:, :, 0].astype(np.float32).tobytes(),
                   "G": img_data[:, :, 1].astype(np.float32).tobytes(),
                   "B": img_data[:, :, 2].astype(np.float32).tobytes()}
            if has_alpha:
                pix["A"] = img_data[:, :, 3].astype(np.float32).tobytes()
            out.writePixels(pix)
            out.close()
            return True
        else:
            # OpenCV: BGR order, float32; no alpha write in OpenCV EXR path
            bgr = np.ascontiguousarray(img_data[:, :, :3][:, :, ::-1].astype(np.float32))
            return cv2.imwrite(filepath, bgr)
    except Exception:
        return False


def load_exr_frame(filepath, return_alpha=False):
    """Load a single EXR frame as RGB float32 (H,W,3) or RGBA (H,W,4) if return_alpha and A exists. Returns None on error."""
    try:
        if USE_OPENEXR:
            f = OpenEXR.InputFile(filepath)
            header = f.header()
            dw = header['dataWindow']
            w = dw.max.x - dw.min.x + 1
            h = dw.max.y - dw.min.y + 1
            channels = sorted(header['channels'].keys())
            rgb = [ch for ch in ['R', 'G', 'B'] if ch in channels]
            if not rgb:
                rgb = channels[:3] if len(channels) >= 3 else channels
            has_alpha = return_alpha and 'A' in header['channels']
            nch = 4 if has_alpha else 3
            img_data = np.zeros((h, w, nch), dtype=np.float32)
            for i, ch in enumerate(rgb[:3]):
                arr, _, _ = read_channel(f, header, ch)
                img_data[:, :, i] = arr.reshape((h, w))
            if has_alpha:
                arr, _, _ = read_channel(f, header, 'A')
                img_data[:, :, 3] = arr.reshape((h, w))
            return img_data
        else:
            # OpenCV doesn't reliably expose EXR alpha; return RGB only
            img = cv2.imread(filepath, cv2.IMREAD_ANYDEPTH | cv2.IMREAD_ANYCOLOR)
            if img is None:
                return None
            if img.dtype != np.float32 and img.dtype != np.float64:
                img = img.astype(np.float32) / (np.iinfo(img.dtype).max if img.dtype.kind in "ui" else 1.0)
            else:
                img = img.astype(np.float32)
            if img.ndim == 2:
                img = np.stack([img, img, img], axis=-1)
            elif img.shape[2] == 1:
                img = np.repeat(img, 3, axis=2)
            elif img.shape[2] >= 3:
                img = img[:, :, :3].copy()
            return np.ascontiguousarray(img[:, :, ::-1], dtype=np.float32)
    except Exception:
        return None


def apply_grading(img, exposure=0.0, gamma=2.2, lift=0.0, gain=1.0, saturation=1.0, alpha_scale=1.0):
    """
    Apply color and alpha grading to linear float image (H,W,3) or (H,W,4).
    Returns same shape. Order: exposure -> lift -> gain -> gamma (RGB) -> saturation (RGB) -> alpha scale (A).
    """
    if img is None or img.size == 0:
        return img
    img = np.clip(img.astype(np.float64), 0, None).astype(np.float32)
    # Exposure
    if exposure != 0.0:
        mult = 2.0 ** float(exposure)
        img = img * mult
    # Lift (add to RGB)
    if lift != 0.0:
        img[:, :, :3] = img[:, :, :3] + float(lift)
    # Gain (multiply RGB)
    if gain != 1.0:
        img[:, :, :3] = img[:, :, :3] * float(gain)
    # Gamma (RGB only)
    if gamma != 1.0 and gamma > 0:
        img[:, :, :3] = np.power(np.clip(img[:, :, :3], 0, None), 1.0 / float(gamma))
    # Saturation (RGB only): mix with luminance
    if saturation != 1.0 and img.shape[2] >= 3:
        lum = 0.2126 * img[:, :, 0] + 0.7152 * img[:, :, 1] + 0.0722 * img[:, :, 2]
        for c in range(3):
            img[:, :, c] = np.clip(lum + (img[:, :, c] - lum) * float(saturation), 0, None)
    # Alpha scale
    if img.shape[2] == 4 and alpha_scale != 1.0:
        img[:, :, 3] = np.clip(img[:, :, 3] * float(alpha_scale), 0, 1)
    return img.astype(np.float32)


# ══════════════════════════════════════════════════════════════════════════════
# .CUBE LUT LOADING AND APPLICATION
# ══════════════════════════════════════════════════════════════════════════════

CUBE_RE_FLOAT = re.compile(r"[-+]?\d*\.\d+|[-+]?\d+")


def _parse_cube_floats(line):
    return [float(x) for x in CUBE_RE_FLOAT.findall(line)]


def load_cube_lut(path_or_bytes, assume_bgr_major=True):
    """
    Load a .cube 3D LUT file. path_or_bytes: file path (str) or file content (bytes).
    Returns (size, domain_min, domain_max, table).
    table shape (size, size, size, 3) RGB output; indexing table[b, g, r] for input (r,g,b).
    """
    if isinstance(path_or_bytes, (str, os.PathLike)):
        with open(path_or_bytes, "rb") as f:
            text = f.read().decode("utf-8", errors="ignore")
    else:
        text = path_or_bytes.decode("utf-8", errors="ignore")
    lines = text.splitlines()
    size = None
    domain_min = np.array([0.0, 0.0, 0.0], dtype=np.float32)
    domain_max = np.array([1.0, 1.0, 1.0], dtype=np.float32)
    data = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        u = line.upper()
        if u.startswith("LUT_3D_SIZE"):
            size = int(line.split()[-1])
            continue
        if u.startswith("DOMAIN_MIN"):
            vals = _parse_cube_floats(line)
            if len(vals) >= 3:
                domain_min = np.array(vals[:3], dtype=np.float32)
            continue
        if u.startswith("DOMAIN_MAX"):
            vals = _parse_cube_floats(line)
            if len(vals) >= 3:
                domain_max = np.array(vals[:3], dtype=np.float32)
            continue
        vals = _parse_cube_floats(line)
        if len(vals) == 3:
            data.append(vals)
    if size is None:
        raise ValueError("LUT_3D_SIZE not found in .cube file.")
    expected = size * size * size
    if len(data) < expected:
        raise ValueError(f".cube incomplete: got {len(data)} rows, expected {expected}.")
    data = np.asarray(data[:expected], dtype=np.float32)
    table = data.reshape((size, size, size, 3))
    if not assume_bgr_major:
        table = table.transpose(2, 1, 0, 3)
    return size, domain_min, domain_max, table


def apply_lut_float(rgb_float, lut_table, domain_min, domain_max, strength=1.0):
    """
    Apply 3D LUT to float RGB (H,W,3) in [0,∞). LUT is (size, size, size, 3).
    domain_min/domain_max (3,) map input to 0..1 for lookup. strength 0=no LUT, 1=full LUT.
    Returns float RGB same shape.
    """
    if rgb_float is None or rgb_float.size == 0 or lut_table is None:
        return rgb_float
    img = np.clip(rgb_float.astype(np.float64), 0, None)
    h, w = img.shape[:2]
    dom_min = np.array(domain_min).reshape(1, 1, 3)
    dom_max = np.array(domain_max).reshape(1, 1, 3)
    denom = np.maximum(dom_max - dom_min, 1e-8)
    x = np.clip((img - dom_min) / denom, 0.0, 1.0)
    s = lut_table.shape[0]
    x = x * (s - 1)
    r, g, b = x[..., 0], x[..., 1], x[..., 2]
    r0 = np.floor(r).astype(np.int32)
    g0 = np.floor(g).astype(np.int32)
    b0 = np.floor(b).astype(np.int32)
    r1 = np.clip(r0 + 1, 0, s - 1)
    g1 = np.clip(g0 + 1, 0, s - 1)
    b1 = np.clip(b0 + 1, 0, s - 1)
    dr = (r - r0).astype(np.float32)
    dg = (g - g0).astype(np.float32)
    db = (b - b0).astype(np.float32)
    r0f, r1f = r0.reshape(-1), r1.reshape(-1)
    g0f, g1f = g0.reshape(-1), g1.reshape(-1)
    b0f, b1f = b0.reshape(-1), b1.reshape(-1)
    drf = dr.reshape(-1)[:, None]
    dgf = dg.reshape(-1)[:, None]
    dbf = db.reshape(-1)[:, None]
    T = lut_table
    c000 = T[b0f, g0f, r0f]
    c100 = T[b0f, g0f, r1f]
    c010 = T[b0f, g1f, r0f]
    c110 = T[b0f, g1f, r1f]
    c001 = T[b1f, g0f, r0f]
    c101 = T[b1f, g0f, r1f]
    c011 = T[b1f, g1f, r0f]
    c111 = T[b1f, g1f, r1f]
    c00 = c000 * (1 - drf) + c100 * drf
    c01 = c001 * (1 - drf) + c101 * drf
    c10 = c010 * (1 - drf) + c110 * drf
    c11 = c011 * (1 - drf) + c111 * drf
    c0 = c00 * (1 - dgf) + c10 * dgf
    c1 = c01 * (1 - dgf) + c11 * dgf
    out = (c0 * (1 - dbf) + c1 * dbf).reshape(h, w, 3).astype(np.float32)
    out = np.clip(out, 0.0, None)
    if strength < 1.0:
        out = img[:, :, :3].astype(np.float32) * (1.0 - strength) + out * strength
    return out.astype(np.float32)


# ══════════════════════════════════════════════════════════════════════════════
# EXPORT TO PRORES / CINEMA FORMATS (via FFmpeg)
# ══════════════════════════════════════════════════════════════════════════════

def _find_ffmpeg():
    """Return path to ffmpeg executable or None."""
    import shutil
    return shutil.which("ffmpeg")

# Codec presets: (display_name, -c:v value, extra args)
_EXPORT_CODECS_MOV = [
    ("ProRes 422 LT", "prores_ks", ["-profile:v", "1"]),
    ("ProRes 422 HQ", "prores_ks", ["-profile:v", "3"]),
    ("ProRes 4444", "prores_ks", ["-profile:v", "4", "-pix_fmt", "yuv444p10le"]),
    ("ProRes 4444 XQ", "prores_ks", ["-profile:v", "5", "-pix_fmt", "yuv444p10le"]),
    ("DNxHR HQX (10-bit)", "dnxhr", ["-profile:v", "dnxhr_hqx"]),
    ("DNxHR 444 (12-bit)", "dnxhr", ["-profile:v", "dnxhr_444"]),
]
_EXPORT_CODECS_MP4 = [
    ("H.264 High", "libx264", ["-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p"]),
    ("H.265 / HEVC", "libx265", ["-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p"]),
]

def _export_sequence_via_ffmpeg(frame_paths, output_path, format_mov, codec_key, scale_vf, fps):
    """
    Export EXR sequence to .mov or .mp4 using FFmpeg.
    format_mov: True = MOV (ProRes/DNx), False = MP4 (H.264/H.265).
    codec_key: index into _EXPORT_CODECS_MOV or _EXPORT_CODECS_MP4.
    scale_vf: None or e.g. "scale=3840:2160".
    Returns (success: bool, message: str).
    """
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        return False, "FFmpeg not found. Install FFmpeg and add it to PATH (see README / IT permissions)."
    if not frame_paths:
        return False, "No frames to export."
    codecs = _EXPORT_CODECS_MOV if format_mov else _EXPORT_CODECS_MP4
    if codec_key < 0 or codec_key >= len(codecs):
        return False, "Invalid codec."
    name, coder, extra = codecs[codec_key]
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        for p in frame_paths:
            esc = p.replace("\\", "/").replace("'", "'\\''")
            f.write("file '%s'\n" % esc)
        list_path = f.name
    try:
        cmd = [
            ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", list_path,
            "-r", str(fps), "-c:v", coder,
        ] + extra
        if not format_mov:
            cmd.extend(["-f", "mp4"])
        if scale_vf:
            cmd.extend(["-vf", scale_vf])
        cmd.append(output_path)
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        if proc.returncode != 0:
            return False, (proc.stderr or proc.stdout or "FFmpeg failed.")[-1500:]
        return True, "Exported to %s" % output_path
    except subprocess.TimeoutExpired:
        return False, "Export timed out."
    except Exception as e:
        return False, str(e)
    finally:
        try:
            os.unlink(list_path)
        except Exception:
            pass


class ExportWorker(QThread):
    """Run export in background and emit result. Optionally apply grading (load frame, grade, write temp, then ffmpeg)."""
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, frame_paths, output_path, format_mov, codec_key, scale_vf, fps, grading_params=None):
        super().__init__()
        self.frame_paths = frame_paths
        self.output_path = output_path
        self.format_mov = format_mov
        self.codec_key = codec_key
        self.scale_vf = scale_vf
        self.fps = fps
        self.grading_params = grading_params or {}

    def run(self):
        paths = self.frame_paths
        if self.grading_params:
            import tempfile
            tmpdir = tempfile.mkdtemp()
            temp_paths = [os.path.join(tmpdir, "frame_%06d.exr" % j) for j in range(len(self.frame_paths))]
            try:
                for i, p in enumerate(self.frame_paths):
                    img = load_exr_frame(p, return_alpha=True)
                    if img is None:
                        self.finished_signal.emit(False, "Failed to load frame: %s" % p)
                        return
                    img = apply_grading(img, **self.grading_params)
                    if not write_exr_frame(temp_paths[i], img):
                        self.finished_signal.emit(False, "Failed to write temp frame.")
                        return
                ok, msg = _export_sequence_via_ffmpeg(
                    temp_paths, self.output_path,
                    self.format_mov, self.codec_key, self.scale_vf, self.fps,
                )
            finally:
                try:
                    for p in temp_paths:
                        if os.path.isfile(p):
                            os.unlink(p)
                    os.rmdir(tmpdir)
                except Exception:
                    pass
        else:
            ok, msg = _export_sequence_via_ffmpeg(
                paths, self.output_path,
                self.format_mov, self.codec_key, self.scale_vf, self.fps,
            )
        self.finished_signal.emit(ok, msg)


class ExportDialog(QDialog):
    """Options for cinema export (format, codec, resolution, fps)."""
    def __init__(self, parent=None, default_fps=24):
        super().__init__(parent)
        self.setWindowTitle("Export to ProRes / Cinema / MP4")
        self.setStyleSheet(STYLESHEET)
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        # Format
        layout.addWidget(QLabel("Output format"))
        self.format_combo = QComboBox()
        self.format_combo.addItem("MOV (ProRes / DNxHR)", True)
        self.format_combo.addItem("MP4 (H.264 / H.265)", False)
        self.format_combo.currentIndexChanged.connect(self._on_format_changed)
        layout.addWidget(self.format_combo)
        # Codec
        layout.addWidget(QLabel("Codec"))
        self.codec_combo = QComboBox()
        self._fill_codecs(format_mov=True)
        layout.addWidget(self.codec_combo)
        # Resolution
        layout.addWidget(QLabel("Resolution"))
        self.res_combo = QComboBox()
        self.res_combo.addItem("Source (no scaling)", None)
        self.res_combo.addItem("4K UHD (3840×2160)", "scale=3840:2160")
        self.res_combo.addItem("4K DCI (4096×2160)", "scale=4096:2160")
        layout.addWidget(self.res_combo)
        # FPS
        layout.addWidget(QLabel("Frame rate (fps)"))
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 120)
        self.fps_spin.setValue(default_fps)
        layout.addWidget(self.fps_spin)
        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton("Export")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)

    def _fill_codecs(self, format_mov):
        self.codec_combo.clear()
        codecs = _EXPORT_CODECS_MOV if format_mov else _EXPORT_CODECS_MP4
        for name, _, _ in codecs:
            self.codec_combo.addItem(name)
        self.codec_combo.setCurrentIndex(0)

    def _on_format_changed(self):
        format_mov = self.format_combo.currentData()
        self._fill_codecs(format_mov)

    def get_options(self):
        format_mov = self.format_combo.currentData()
        return {
            "format_mov": format_mov,
            "codec_key": self.codec_combo.currentIndex(),
            "scale_vf": self.res_combo.currentData(),
            "fps": self.fps_spin.value(),
        }


# ══════════════════════════════════════════════════════════════════════════════
# FULLSCREEN DIALOG
# ══════════════════════════════════════════════════════════════════════════════

class FullscreenDialog(QDialog):
    """Fullscreen dialog for detailed visualization."""
    
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setStyleSheet(STYLESHEET)
        self.setMinimumSize(1200, 800)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Toolbar
        self.toolbar_widget = QWidget()
        toolbar_layout = QHBoxLayout(self.toolbar_widget)
        toolbar_layout.setContentsMargins(10, 10, 10, 10)
        
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont('SF Pro Display', 16, QFont.Bold))
        toolbar_layout.addWidget(self.title_label)
        toolbar_layout.addStretch()
        
        self.close_btn = QPushButton("✕ Close")
        self.close_btn.clicked.connect(self.close)
        toolbar_layout.addWidget(self.close_btn)
        
        layout.addWidget(self.toolbar_widget)
        
        # Content area
        self.content_layout = QVBoxLayout()
        layout.addLayout(self.content_layout)
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        super().keyPressEvent(event)


# ══════════════════════════════════════════════════════════════════════════════
# INTERACTIVE MATPLOTLIB WIDGETS
# ══════════════════════════════════════════════════════════════════════════════

class InteractiveCanvas(FigureCanvas):
    """Base class for interactive matplotlib canvases with zoom/pan."""
    
    fullscreen_requested = pyqtSignal()
    
    def __init__(self, figsize=(8, 4), parent=None):
        self.fig = Figure(figsize=figsize, facecolor=COLORS['bg_card'])
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax = self.fig.add_subplot(111)
        self._setup_axes()
        
        # Enable mouse interaction
        self.setFocusPolicy(Qt.StrongFocus)
        self.mpl_connect('scroll_event', self._on_scroll)
        self.mpl_connect('button_press_event', self._on_press)
        self.mpl_connect('button_release_event', self._on_release)
        self.mpl_connect('motion_notify_event', self._on_motion)
        
        self._pan_start = None
        self._pan_xlim = None
        self._pan_ylim = None
        # Optional: (x_min, x_max, y_min, y_max) to constrain pan/zoom to data + 10%
        self._view_limits = None

    def set_view_limits(self, x_min, x_max, y_min, y_max):
        """Constrain pan/zoom to these bounds (e.g. data range + 10%)."""
        self._view_limits = (x_min, x_max, y_min, y_max)

    def _clamp_limits(self, xlim, ylim):
        """Clamp xlim, ylim to _view_limits if set."""
        if self._view_limits is None:
            return xlim, ylim
        x_lo, x_hi, y_lo, y_hi = self._view_limits
        nx0 = max(x_lo, min(x_hi, xlim[0]))
        nx1 = max(x_lo, min(x_hi, xlim[1]))
        if nx0 == nx1:
            nx1 = nx0 + (x_hi - x_lo) * 0.01
        ny0 = max(y_lo, min(y_hi, ylim[0]))
        ny1 = max(y_lo, min(y_hi, ylim[1]))
        if ny0 == ny1:
            ny1 = ny0 + (y_hi - y_lo) * 0.01
        return (nx0, nx1), (ny0, ny1)

    def _setup_axes(self):
        self.ax.set_facecolor(COLORS['bg'])
        self.ax.tick_params(colors=COLORS['text_dim'], labelsize=9)
        for spine in self.ax.spines.values():
            spine.set_color(COLORS['border'])
        self.ax.grid(True, color=COLORS['border'], alpha=0.3, linestyle='-', linewidth=0.5)
    
    def _on_scroll(self, event):
        """Zoom with scroll wheel."""
        if event.inaxes != self.ax:
            return
        
        scale = 1.2 if event.button == 'down' else 1/1.2
        
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        
        xdata = event.xdata
        ydata = event.ydata
        
        new_xlim = [xdata - (xdata - xlim[0]) * scale,
                    xdata + (xlim[1] - xdata) * scale]
        new_ylim = [ydata - (ydata - ylim[0]) * scale,
                    ydata + (ylim[1] - ydata) * scale]
        new_xlim, new_ylim = self._clamp_limits(new_xlim, new_ylim)
        self.ax.set_xlim(new_xlim)
        self.ax.set_ylim(new_ylim)
        self.draw()
    
    def _on_press(self, event):
        """Start pan on middle click or right click."""
        if event.button in [2, 3] and event.inaxes == self.ax:
            self._pan_start = (event.x, event.y)
            self._pan_xlim = self.ax.get_xlim()
            self._pan_ylim = self.ax.get_ylim()
            self.setCursor(QCursor(Qt.ClosedHandCursor))
    
    def _on_release(self, event):
        """End pan."""
        self._pan_start = None
        self.setCursor(QCursor(Qt.ArrowCursor))
    
    def _on_motion(self, event):
        """Pan while dragging."""
        if self._pan_start is None:
            return
        
        dx = event.x - self._pan_start[0]
        dy = event.y - self._pan_start[1]
        
        # Convert pixel delta to data delta
        xlim = self._pan_xlim
        ylim = self._pan_ylim
        
        # Get axes dimensions in pixels
        bbox = self.ax.get_window_extent()
        
        dx_data = -dx * (xlim[1] - xlim[0]) / bbox.width
        dy_data = -dy * (ylim[1] - ylim[0]) / bbox.height  # negate so drag-down moves content down
        
        new_xlim = [xlim[0] + dx_data, xlim[1] + dx_data]
        new_ylim = [ylim[0] + dy_data, ylim[1] + dy_data]
        new_xlim, new_ylim = self._clamp_limits(new_xlim, new_ylim)
        self.ax.set_xlim(new_xlim)
        self.ax.set_ylim(new_ylim)
        self.draw()

    def reset_view(self):
        """Reset to default view - override in subclasses."""
        pass


# Max x points for waveform (keeps zoom/pan fast while preserving shape)
WAVEFORM_MAX_POINTS = 1200


def _hex_to_rgba(hex_color, alpha=255):
    """Convert #RRGGBB to (r, g, b, a) 0-255."""
    hex_color = hex_color.lstrip('#')
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return (r, g, b, alpha)


# Max points for FULL waveform scatter (keeps zoom/pan responsive)
WAVEFORM_FULL_MAX_POINTS = 150000


class WaveformWidget(QWidget):
    """DaVinci Resolve-style waveform using pyqtgraph: sharp, transparent RGB, fast zoom/pan."""
    hint_text = "Scroll: Zoom | Left-drag: Pan"

    def __init__(self, parent=None, fullscreen=False):
        super().__init__(parent)
        self.img_data = None
        self.max_display = 1.1
        self.fullscreen = fullscreen
        self._full_spectrum = False  # False = envelope (line) view, True = FULL waveform
        self._channel_visible = [True, True, True]  # R, G, B
        self._plot_items = []
        self._ref_lines = []

        pg.setConfigOptions(antialias=True, background=COLORS['bg_card'])
        try:
            pg.setConfigOptions(useOpenGL=True)
        except Exception:
            pass

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Row: FULL waveform toggle + R, G, B channel toggles (larger hit area for easier clicking)
        toggle_row = QHBoxLayout()
        _toggle_style = f"""
            QCheckBox {{
                color: {COLORS['text_dim']};
                font-size: 13px;
                font-weight: 500;
                padding: 10px 14px;
                min-height: 24px;
                spacing: 10px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {COLORS['border']};
                border-radius: 4px;
                background: {COLORS['bg_light']};
            }}
            QCheckBox::indicator:checked {{
                background: {COLORS['accent']};
                border-color: {COLORS['accent']};
            }}
            QCheckBox:checked {{ color: {COLORS['text']}; }}
        """
        self._full_check = QCheckBox("FULL waveform")
        self._full_check.setStyleSheet(_toggle_style)
        self._full_check.setToolTip("Show full spectrum (all points) vs envelope (min/max bands)")
        self._full_check.setCursor(Qt.PointingHandCursor)
        self._full_check.toggled.connect(self._on_full_toggled)
        toggle_row.addWidget(self._full_check)
        toggle_row.addSpacing(12)
        self._r_check = QCheckBox("R")
        self._r_check.setStyleSheet(_toggle_style)
        self._r_check.setChecked(True)
        self._r_check.setCursor(Qt.PointingHandCursor)
        self._r_check.toggled.connect(lambda _: self._on_channel_toggled())
        toggle_row.addWidget(self._r_check)
        self._g_check = QCheckBox("G")
        self._g_check.setStyleSheet(_toggle_style)
        self._g_check.setChecked(True)
        self._g_check.setCursor(Qt.PointingHandCursor)
        self._g_check.toggled.connect(lambda _: self._on_channel_toggled())
        toggle_row.addWidget(self._g_check)
        self._b_check = QCheckBox("B")
        self._b_check.setStyleSheet(_toggle_style)
        self._b_check.setChecked(True)
        self._b_check.setCursor(Qt.PointingHandCursor)
        self._b_check.toggled.connect(lambda _: self._on_channel_toggled())
        toggle_row.addWidget(self._b_check)
        toggle_row.addStretch()
        layout.addLayout(toggle_row)

        self._plot = pg.PlotWidget(parent=self)
        self._plot.setMinimumHeight(280 if fullscreen else 120)
        layout.addWidget(self._plot)

        self._plot.setBackground(COLORS['bg_card'])
        self._plot.getAxis('left').setPen(pg.mkPen(COLORS['text_dim']))
        self._plot.getAxis('left').setTextPen(COLORS['text_dim'])
        self._plot.getAxis('bottom').setPen(pg.mkPen(COLORS['text_dim']))
        self._plot.getAxis('bottom').setTextPen(COLORS['text_dim'])
        self._plot.showGrid(x=True, y=True, alpha=0.3)
        self._plot.setLabel('left', 'Level')
        self._plot.setLabel('bottom', 'Frame Position')

    def _on_full_toggled(self, checked):
        self._full_spectrum = checked
        if self.img_data is not None:
            self._render()

    def _on_channel_toggled(self):
        if self.img_data is not None:
            self._render()

    def update_waveform(self, img_data, max_display=1.1):
        """Generate waveform from image data: envelope or full spectrum depending on toggle."""
        self.img_data = img_data
        self.max_display = max_display
        self._render()

    def _render(self):
        self._plot.clear()
        self._plot_items.clear()
        self._ref_lines.clear()

        if self.img_data is None:
            return

        self._channel_visible = [
            self._r_check.isChecked(),
            self._g_check.isChecked(),
            self._b_check.isChecked(),
        ]

        if self._full_spectrum:
            self._render_full_spectrum()
        else:
            self._render_envelope()

        # Reference lines (shared)
        for level in [0.25, 0.5, 0.75, 1.0]:
            line = pg.InfiniteLine(pos=level, angle=0, pen=pg.mkPen(COLORS['border'], style=Qt.DashLine, width=1))
            self._plot.addItem(line)
            self._ref_lines.append(line)

        self._plot.setXRange(0, 1)
        self._plot.setYRange(0, self.max_display)
        # Constrain pan/zoom to data range + 10%
        x_span, y_span = 1.0, self.max_display
        pad_x, pad_y = 0.1 * x_span, 0.1 * y_span
        vb = self._plot.getViewBox()
        vb.setLimits(
            xMin=0 - pad_x, xMax=1 + pad_x,
            yMin=0 - pad_y, yMax=self.max_display + pad_y,
        )

    def _render_envelope(self):
        """Envelope view: min/max bands per channel (line/fill)."""
        h, w, c = self.img_data.shape
        n_cols = min(WAVEFORM_MAX_POINTS, w)
        col_indices = np.linspace(0, w - 1, n_cols).astype(np.intp)
        x = np.linspace(0.0, 1.0, n_cols)

        colors_rgba = [
            _hex_to_rgba(COLORS['red'], 160),
            _hex_to_rgba(COLORS['green'], 160),
            _hex_to_rgba(COLORS['blue'], 160),
        ]

        for ch_idx in range(3):
            if not self._channel_visible[ch_idx]:
                continue
            channel = self.img_data[:, col_indices, ch_idx]
            if channel.size == 0:
                continue
            y_min = np.nanmin(channel, axis=0)
            y_max = np.nanmax(channel, axis=0)
            y_min = np.clip(y_min, 0.0, self.max_display)
            y_max = np.clip(y_max, 0.0, self.max_display)

            curve_top = pg.PlotDataItem(x, y_max, pen=None)
            curve_bot = pg.PlotDataItem(x, y_min, pen=None)
            brush = pg.mkBrush(*colors_rgba[ch_idx])
            fill = pg.FillBetweenItem(curve_bot, curve_top, brush=brush)
            self._plot.addItem(fill)
            self._plot.addItem(curve_top)
            self._plot.addItem(curve_bot)
            pen = pg.mkPen(color=colors_rgba[ch_idx], width=1)
            curve_top.setPen(pen)
            curve_bot.setPen(pen)
            self._plot_items.extend([fill, curve_top, curve_bot])

    def _render_full_spectrum(self):
        """FULL waveform: scatter of sampled points (full spectrum, one scatter per channel)."""
        h, w, c = self.img_data.shape
        max_pts = WAVEFORM_FULL_MAX_POINTS
        n_cols_full = min(500, w)
        n_rows_full = min(h, max(1, max_pts // n_cols_full))

        col_indices = np.linspace(0, w - 1, n_cols_full).astype(np.intp)
        row_indices = np.linspace(0, h - 1, n_rows_full).astype(np.intp)

        x_positions = np.linspace(0.0, 1.0, n_cols_full)
        x_all = np.repeat(x_positions, n_rows_full)

        colors_rgba = [
            _hex_to_rgba(COLORS['red'], 120),
            _hex_to_rgba(COLORS['green'], 120),
            _hex_to_rgba(COLORS['blue'], 120),
        ]

        for ch_idx in range(3):
            if not self._channel_visible[ch_idx]:
                continue
            channel = self.img_data[:, :, ch_idx][np.ix_(row_indices, col_indices)]
            y_all = np.clip(channel.ravel(), 0.0, self.max_display)

            item = pg.PlotDataItem(
                x_all, y_all,
                pen=None,
                symbol='o',
                symbolSize=1.5,
                symbolBrush=pg.mkBrush(*colors_rgba[ch_idx]),
                symbolPen=None,
            )
            self._plot.addItem(item)
            self._plot_items.append(item)

    def reset_view(self):
        self._plot.setXRange(0, 1)
        self._plot.setYRange(0, self.max_display)


class HistogramCanvas(InteractiveCanvas):
    """Matplotlib canvas that draws the RGB histogram (used inside HistogramWidget)."""
    def __init__(self, parent=None, fullscreen=False):
        figsize = (12, 6) if fullscreen else (8, 3)
        super().__init__(figsize=figsize, parent=parent)
        self.info = None
        self.fullscreen = fullscreen
        self._channel_visible = [True, True, True]
        self._y_cap = 10.0  # density axis cap (from 99.5th percentile)

    def update_histogram(self, info, channel_visible=None):
        self.info = info
        if channel_visible is not None:
            self._channel_visible = channel_visible
        self._render()

    def _render(self):
        self.ax.clear()
        self._setup_axes()
        # Always set view limits first (even when no data) so pan/zoom never go infinite
        _x_lo, _x_hi = -0.26, 1.66  # data -0.1..1.5 + 10%
        _y_lo, _y_hi = 0.0, 100.0  # density: fixed max so we never get huge numbers
        self.set_view_limits(_x_lo, _x_hi, _y_lo, _y_hi)
        if self.info is None:
            self.draw()
            return
        colors_list = [COLORS['red'], COLORS['green'], COLORS['blue']]
        channels = ['R', 'G', 'B']
        n_bins = 512 if self.fullscreen else 256
        bin_edges = np.linspace(-0.1, 2.0, n_bins + 1)
        all_densities = []
        for i, (ch, color) in enumerate(zip(channels, colors_list)):
            if not self._channel_visible[i]:
                continue
            if ch in self.info['results']:
                data = self.info['results'][ch]['data']
                data_clipped = np.clip(data, -0.1, 2.0)
                counts, _ = np.histogram(data_clipped, bins=bin_edges, density=False)
                density = counts / (data_clipped.size * (bin_edges[1] - bin_edges[0]))
                all_densities.append(density)
                self.ax.hist(data_clipped, bins=bin_edges, color=color, alpha=0.5,
                             density=True, histtype='stepfilled', label=ch)
        self.ax.set_xlim(-0.1, 1.5)
        self.ax.set_ylabel('Density', color=COLORS['text_dim'], fontsize=10)
        self.ax.set_xlabel('Value', color=COLORS['text_dim'], fontsize=10)
        self.ax.axvline(x=1.0, color=COLORS['warning'], linestyle='--', linewidth=1, alpha=0.7, label='1.0')
        self.ax.axvline(x=0.0, color=COLORS['text_dim'], linestyle='--', linewidth=0.5, alpha=0.5)
        if self.fullscreen:
            self.ax.legend(loc='upper right', facecolor=COLORS['bg_light'], edgecolor=COLORS['border'])
        # Cap y-axis by 99.5th percentile of density so the spike at 1.0 doesn't dominate
        if all_densities:
            combined = np.concatenate([d.ravel() for d in all_densities])
            combined = combined[np.isfinite(combined) & (combined > 0)]
            y_cap = np.percentile(combined, 99.5) if combined.size > 0 else 10.0
            y_cap = max(y_cap * 1.1, 0.5)
            y_cap = min(y_cap, 100.0)
        else:
            y_cap = 10.0
        self._y_cap = y_cap
        self.ax.set_ylim(0, y_cap)
        self.fig.tight_layout()
        self.draw()
        y_lo, y_hi = 0.0, min(100.0, y_cap * 1.1)
        self.set_view_limits(_x_lo, _x_hi, y_lo, y_hi)
        cur_x, cur_y = self.ax.get_xlim(), self.ax.get_ylim()
        cur_x, cur_y = self._clamp_limits(cur_x, cur_y)
        self.ax.set_xlim(cur_x)
        self.ax.set_ylim(cur_y)
        self.draw_idle()

    def reset_view(self):
        self.ax.set_xlim(-0.1, 1.5)
        self.ax.set_ylim(0, self._y_cap)
        self.draw()
        y_pad = 0.1 * self._y_cap
        self.set_view_limits(-0.26, 1.66, 0, min(100, self._y_cap + y_pad))


# Shared style for R/G/B toggles (waveform and histogram)
def _channel_toggle_style():
    return f"""
        QCheckBox {{
            color: {COLORS['text_dim']};
            font-size: 13px;
            font-weight: 500;
            padding: 10px 14px;
            min-height: 24px;
            spacing: 10px;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {COLORS['border']};
            border-radius: 4px;
            background: {COLORS['bg_light']};
        }}
        QCheckBox::indicator:checked {{
            background: {COLORS['accent']};
            border-color: {COLORS['accent']};
        }}
        QCheckBox:checked {{ color: {COLORS['text']}; }}
    """


class HistogramWidget(QWidget):
    """Histogram panel with R, G, B channel toggles."""
    hint_text = "Scroll: Zoom | Right-drag: Pan"

    def __init__(self, parent=None, fullscreen=False):
        super().__init__(parent)
        self.info = None
        self.fullscreen = fullscreen
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        toggle_row = QHBoxLayout()
        _style = _channel_toggle_style()
        self._r_check = QCheckBox("R")
        self._r_check.setStyleSheet(_style)
        self._r_check.setChecked(True)
        self._r_check.setCursor(Qt.PointingHandCursor)
        self._r_check.toggled.connect(self._on_channel_toggled)
        toggle_row.addWidget(self._r_check)
        self._g_check = QCheckBox("G")
        self._g_check.setStyleSheet(_style)
        self._g_check.setChecked(True)
        self._g_check.setCursor(Qt.PointingHandCursor)
        self._g_check.toggled.connect(self._on_channel_toggled)
        toggle_row.addWidget(self._g_check)
        self._b_check = QCheckBox("B")
        self._b_check.setStyleSheet(_style)
        self._b_check.setChecked(True)
        self._b_check.setCursor(Qt.PointingHandCursor)
        self._b_check.toggled.connect(self._on_channel_toggled)
        toggle_row.addWidget(self._b_check)
        toggle_row.addStretch()
        layout.addLayout(toggle_row)
        self._canvas = HistogramCanvas(parent=self, fullscreen=fullscreen)
        # Min height: smaller in main view so histogram isn't too big; larger in fullscreen
        self._canvas.setMinimumHeight(380 if fullscreen else 160)
        layout.addWidget(self._canvas)

    def _on_channel_toggled(self):
        if self.info is not None:
            self._canvas.update_histogram(self.info, channel_visible=self._channel_visible())

    def _channel_visible(self):
        return [
            self._r_check.isChecked(),
            self._g_check.isChecked(),
            self._b_check.isChecked(),
        ]

    def update_histogram(self, info):
        self.info = info
        self._canvas.update_histogram(info, channel_visible=self._channel_visible())

    def reset_view(self):
        self._canvas.reset_view()


class ImagePreviewWidget(InteractiveCanvas):
    """Zoomable image preview."""
    
    def __init__(self, parent=None, fullscreen=False):
        figsize = (12, 10) if fullscreen else (6, 4)
        super().__init__(figsize=figsize, parent=parent)
        self.img_data = None
        self.exposure = 0.0
        self.fullscreen = fullscreen
        self.ax.set_axis_off()
    
    def update_image(self, img_data, exposure=0.0):
        """Update preview with tone-mapped image."""
        self.img_data = img_data
        self.exposure = exposure
        self._render()
    
    def _render(self):
        self.ax.clear()
        self.ax.set_axis_off()
        
        if self.img_data is None:
            self.ax.text(0.5, 0.5, 'No image loaded', ha='center', va='center', 
                        color=COLORS['text_dim'], fontsize=12, transform=self.ax.transAxes)
            self.draw()
            return
        
        # Tone mapping
        exposure_mult = 2.0 ** self.exposure
        img = self.img_data * exposure_mult
        img = img / (1.0 + img)  # Reinhard
        img = np.power(np.clip(img, 0, 1), 1.0/2.2)  # Gamma
        
        self.ax.imshow(img, aspect='auto')
        self.ax.set_xlim(0, img.shape[1])
        self.ax.set_ylim(img.shape[0], 0)
        
        self.fig.tight_layout()
        self.draw()
    
    def reset_view(self):
        if self.img_data is not None:
            self.ax.set_xlim(0, self.img_data.shape[1])
            self.ax.set_ylim(self.img_data.shape[0], 0)
            self.draw()


def _tonemap_for_display(img_float):
    """Reinhard + gamma for display (same as ImagePreviewWidget)."""
    if img_float is None or img_float.size == 0:
        return None
    img = np.clip(img_float.astype(np.float64), 0, None)
    img = img / (1.0 + img)
    return np.power(np.clip(img, 0, 1), 1.0 / 2.2).astype(np.float32)


class SplitComparisonWidget(QWidget):
    """Before/after split view with draggable divider (JuxtaposeJS-style)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(STYLESHEET)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.img_left = None
        self.img_right = None
        self.label_left = "Original"
        self.label_right = "LUT"
        self.split_ratio = 0.5
        self._fig = Figure(figsize=(8, 5), facecolor=COLORS['bg_card'])
        self._canvas = FigureCanvas(self._fig)
        self._canvas.setMinimumHeight(300)
        self.ax = self._fig.add_axes([0, 0, 1, 1], facecolor=COLORS['bg_card'])
        self.ax.set_axis_off()
        layout.addWidget(self._canvas)
        slider_row = QHBoxLayout()
        slider_row.addWidget(QLabel("← Original"))
        self.split_slider = QSlider(Qt.Horizontal)
        self.split_slider.setRange(0, 1000)
        self.split_slider.setValue(500)
        self.split_slider.valueChanged.connect(self._on_slider)
        slider_row.addWidget(self.split_slider, stretch=1)
        slider_row.addWidget(QLabel("LUT →"))
        layout.addLayout(slider_row)
        self._render()

    def _on_slider(self, val):
        self.split_ratio = val / 1000.0
        self._render()

    def update_comparison(self, img_left, img_right, label_left="Original", label_right="LUT"):
        self.img_left = img_left
        self.img_right = img_right
        self.label_left = label_left
        self.label_right = label_right
        self._render()

    def _render(self):
        self.ax.clear()
        self.ax.set_axis_off()
        if self.img_left is None and self.img_right is None:
            self.ax.text(0.5, 0.5, "No comparison — load a frame and enable LUT compare", ha='center', va='center',
                        color=COLORS['text_dim'], fontsize=11, transform=self.ax.transAxes)
            self._canvas.draw()
            return
        split = self.split_ratio
        H, W = 0, 0
        if self.img_left is not None:
            H, W = self.img_left.shape[:2]
        if self.img_right is not None and self.img_right.size > 0:
            h, w = self.img_right.shape[:2]
            H, W = max(H, h), max(W, w)
        if H == 0 or W == 0:
            self._canvas.draw()
            return
        # Use same aspect and extent 0..1 so split is in normalized coords
        self.ax.set_xlim(0, 1)
        self.ax.set_ylim(1, 0)
        self.ax.set_aspect("auto")
        if self.img_left is not None:
            L = _tonemap_for_display(self.img_left[:, :, :3])
            if L is not None:
                self.ax.imshow(L, extent=[0, split, 1, 0], aspect="auto", interpolation="bilinear")
        if self.img_right is not None and self.img_right.size > 0:
            R = _tonemap_for_display(self.img_right[:, :, :3])
            if R is not None:
                self.ax.imshow(R, extent=[split, 1, 1, 0], aspect="auto", interpolation="bilinear")
        self.ax.axvline(x=split, color='white', linewidth=2, linestyle='-')
        self.ax.text(0.02, 0.98, self.label_left, fontsize=10, color='white', verticalalignment='top',
                     bbox=dict(boxstyle='round,pad=0.3', facecolor='#333', alpha=0.9))
        self.ax.text(0.98, 0.98, self.label_right, fontsize=10, color='white', verticalalignment='top',
                     horizontalalignment='right',
                     bbox=dict(boxstyle='round,pad=0.3', facecolor='#333', alpha=0.9))
        self._canvas.draw_idle()


# ══════════════════════════════════════════════════════════════════════════════
# LUT PANEL (folder, dropdown, strength, compare mode)
# ══════════════════════════════════════════════════════════════════════════════

class LUTPanel(QWidget):
    """LUT folder path, dropdown selection, strength slider+spinbox, compare mode (Original vs LUT / LUT A vs LUT B)."""
    lut_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(STYLESHEET)
        self.setMinimumWidth(260)
        self.setMaximumWidth(340)
        self._lut_dir = ""
        self._lut_paths = []
        self._lut_cache = {}  # path -> (size, domain_min, domain_max, table)
        self._assume_bgr = True
        layout = QVBoxLayout(self)
        grp = QGroupBox("LUT (.cube)")
        grp.setStyleSheet("QGroupBox { font-weight: 600; }")
        self._lut_grp = grp
        gl = QVBoxLayout(grp)
        self.enable_cb = QCheckBox("Enable LUT")
        self.enable_cb.setChecked(True)
        self.enable_cb.toggled.connect(self._on_enable_toggled)
        gl.addWidget(self.enable_cb)
        row = QHBoxLayout()
        self.folder_btn = QPushButton("LUT folder…")
        self.folder_btn.clicked.connect(self._pick_folder)
        row.addWidget(self.folder_btn)
        self.path_label = QLabel("No folder")
        self.path_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 10px;")
        self.path_label.setWordWrap(True)
        row.addWidget(self.path_label, stretch=1)
        gl.addLayout(row)
        gl.addWidget(QLabel("LUT A"))
        self.lut_a_combo = QComboBox()
        self.lut_a_combo.currentIndexChanged.connect(self._emit)
        gl.addWidget(self.lut_a_combo)
        strength_row = QHBoxLayout()
        strength_row.addWidget(QLabel("Strength A"))
        self.strength_slider = QSlider(Qt.Horizontal)
        self.strength_slider.setRange(0, 1000)
        self.strength_slider.setValue(1000)
        self.strength_slider.valueChanged.connect(self._sync_strength_to_spin)
        strength_row.addWidget(self.strength_slider, stretch=1)
        self.strength_spin = QDoubleSpinBox()
        self.strength_spin.setRange(0.0, 1.0)
        self.strength_spin.setValue(1.0)
        self.strength_spin.setDecimals(2)
        self.strength_spin.setSingleStep(0.05)
        self.strength_spin.setMinimumWidth(52)
        self.strength_spin.valueChanged.connect(self._sync_strength_to_slider)
        strength_row.addWidget(self.strength_spin)
        gl.addLayout(strength_row)
        gl.addWidget(QLabel("Compare"))
        self.compare_combo = QComboBox()
        self.compare_combo.addItem("Off", "off")
        self.compare_combo.addItem("Original vs LUT A", "original_vs_a")
        self.compare_combo.addItem("LUT A vs LUT B", "a_vs_b")
        self.compare_combo.currentIndexChanged.connect(self._on_compare_mode)
        gl.addWidget(self.compare_combo)
        self._lut_b_label = QLabel("LUT B")
        gl.addWidget(self._lut_b_label)
        self.lut_b_combo = QComboBox()
        self.lut_b_combo.currentIndexChanged.connect(self._emit)
        gl.addWidget(self.lut_b_combo)
        self.lut_b_combo.setVisible(False)
        self._lut_b_label.setVisible(False)
        self._strength_b_label = QLabel("Strength B")
        gl.addWidget(self._strength_b_label)
        strength_b_row = QHBoxLayout()
        self.strength_b_slider = QSlider(Qt.Horizontal)
        self.strength_b_slider.setRange(0, 1000)
        self.strength_b_slider.setValue(1000)
        self.strength_b_slider.valueChanged.connect(self._sync_strength_b_to_spin)
        strength_b_row.addWidget(self.strength_b_slider, stretch=1)
        self.strength_b_spin = QDoubleSpinBox()
        self.strength_b_spin.setRange(0.0, 1.0)
        self.strength_b_spin.setValue(1.0)
        self.strength_b_spin.setDecimals(2)
        self.strength_b_spin.setSingleStep(0.05)
        self.strength_b_spin.setMinimumWidth(52)
        self.strength_b_spin.valueChanged.connect(self._sync_strength_b_to_slider)
        strength_b_row.addWidget(self.strength_b_spin)
        gl.addLayout(strength_b_row)
        self._strength_b_label.setVisible(False)
        self.strength_b_slider.setVisible(False)
        self.strength_b_spin.setVisible(False)
        self.assume_cb = QCheckBox("Alternate .cube order (if colors wrong)")
        self.assume_cb.setChecked(False)
        self.assume_cb.toggled.connect(self._on_assume)
        gl.addWidget(self.assume_cb)
        layout.addWidget(grp)
        # Default: point to lut folder in project root, life_is_a_lemon.cube at 0.20
        self._set_default_lut_folder()

    def _set_default_lut_folder(self):
        default_dir = os.path.join(_ROOT, "lut")
        if not os.path.isdir(default_dir):
            return
        self._lut_dir = default_dir
        self.path_label.setText(os.path.basename(default_dir) or "lut")
        paths = []
        for name in sorted(os.listdir(default_dir)):
            if name.lower().endswith(".cube"):
                paths.append(os.path.join(default_dir, name))
        self._lut_paths = paths
        self._lut_cache.clear()
        self.lut_a_combo.blockSignals(True)
        self.lut_b_combo.blockSignals(True)
        self.lut_a_combo.clear()
        self.lut_b_combo.clear()
        for p in paths:
            name = os.path.basename(p)
            self.lut_a_combo.addItem(name, p)
            self.lut_b_combo.addItem(name, p)
        default_lut_name = "life_is_a_lemon.cube"
        idx_a = next((i for i in range(self.lut_a_combo.count()) if self.lut_a_combo.itemText(i) == default_lut_name), 0)
        self.lut_a_combo.setCurrentIndex(idx_a)
        self.lut_b_combo.setCurrentIndex(min(idx_a + 1, self.lut_b_combo.count() - 1) if self.lut_b_combo.count() > 1 else 0)
        self.lut_a_combo.blockSignals(False)
        self.lut_b_combo.blockSignals(False)
        self.strength_slider.blockSignals(True)
        self.strength_spin.blockSignals(True)
        self.strength_slider.setValue(200)
        self.strength_spin.setValue(0.20)
        self.strength_slider.blockSignals(False)
        self.strength_spin.blockSignals(False)

    def _pick_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select folder containing .cube files", self._lut_dir or "")
        if not folder:
            return
        self._lut_dir = folder
        self.path_label.setText(os.path.basename(folder) or folder)
        paths = []
        for name in sorted(os.listdir(folder)):
            if name.lower().endswith(".cube"):
                paths.append(os.path.join(folder, name))
        self._lut_paths = paths
        self._lut_cache.clear()
        self.lut_a_combo.clear()
        self.lut_b_combo.clear()
        for p in paths:
            name = os.path.basename(p)
            self.lut_a_combo.addItem(name, p)
            self.lut_b_combo.addItem(name, p)
        if paths:
            self.lut_a_combo.setCurrentIndex(0)
            self.lut_b_combo.setCurrentIndex(min(1, len(paths) - 1))
        self.lut_changed.emit()

    def _on_compare_mode(self):
        is_ab = self.compare_combo.currentData() == "a_vs_b"
        self.lut_b_combo.setVisible(is_ab)
        self._lut_b_label.setVisible(is_ab)
        self._strength_b_label.setVisible(is_ab)
        self.strength_b_slider.setVisible(is_ab)
        self.strength_b_spin.setVisible(is_ab)
        self.lut_changed.emit()

    def _on_enable_toggled(self, checked):
        enabled = checked
        self.folder_btn.setEnabled(enabled)
        self.path_label.setEnabled(enabled)
        self.lut_a_combo.setEnabled(enabled)
        self.strength_slider.setEnabled(enabled)
        self.strength_spin.setEnabled(enabled)
        self.compare_combo.setEnabled(enabled)
        self._lut_b_label.setEnabled(enabled)
        self.lut_b_combo.setEnabled(enabled)
        self._strength_b_label.setEnabled(enabled)
        self.strength_b_slider.setEnabled(enabled)
        self.strength_b_spin.setEnabled(enabled)
        self.assume_cb.setEnabled(enabled)
        self.lut_changed.emit()

    def _sync_strength_b_to_spin(self):
        self.strength_b_spin.setValue(self.strength_b_slider.value() / 1000.0)
        self._emit()

    def _sync_strength_b_to_slider(self):
        self.strength_b_slider.blockSignals(True)
        self.strength_b_slider.setValue(int(self.strength_b_spin.value() * 1000))
        self.strength_b_slider.blockSignals(False)
        self._emit()

    def _on_assume(self, checked):
        self._assume_bgr = not checked
        self._lut_cache.clear()
        self.lut_changed.emit()

    def _sync_strength_to_spin(self):
        self.strength_spin.setValue(self.strength_slider.value() / 1000.0)

    def _sync_strength_to_slider(self):
        self.strength_slider.blockSignals(True)
        self.strength_slider.setValue(int(self.strength_spin.value() * 1000))
        self.strength_slider.blockSignals(False)
        self._emit()

    def _emit(self):
        self.lut_changed.emit()

    def get_lut_dir(self):
        return self._lut_dir

    def get_compare_mode(self):
        return self.compare_combo.currentData()

    def get_strength_a(self):
        return self.strength_spin.value()

    def get_strength_b(self):
        return self.strength_b_spin.value()

    def is_enabled(self):
        return self.enable_cb.isChecked()

    def get_lut_a_path(self):
        if not self.is_enabled() or self.lut_a_combo.count() == 0:
            return None
        return self.lut_a_combo.currentData()

    def get_lut_b_path(self):
        if not self.is_enabled() or self.compare_combo.currentData() != "a_vs_b" or self.lut_b_combo.count() == 0:
            return None
        return self.lut_b_combo.currentData()

    def _load_lut(self, path):
        if path is None:
            return None
        if path in self._lut_cache:
            return self._lut_cache[path]
        try:
            size, dmin, dmax, table = load_cube_lut(path, assume_bgr_major=self._assume_bgr)
            self._lut_cache[path] = (size, dmin, dmax, table)
            return self._lut_cache[path]
        except Exception:
            return None

    def apply_lut_a(self, rgb_float):
        path = self.get_lut_a_path()
        if path is None or rgb_float is None:
            return rgb_float
        lut = self._load_lut(path)
        if lut is None:
            return rgb_float
        size, dmin, dmax, table = lut
        return apply_lut_float(rgb_float, table, dmin, dmax, strength=self.get_strength_a())

    def apply_lut_b(self, rgb_float):
        path = self.get_lut_b_path()
        if path is None or rgb_float is None:
            return rgb_float
        lut = self._load_lut(path)
        if lut is None:
            return rgb_float
        size, dmin, dmax, table = lut
        return apply_lut_float(rgb_float, table, dmin, dmax, strength=self.get_strength_b())

    def get_left_right_for_compare(self, graded_rgb):
        """Return (img_left, img_right, label_left, label_right) for current compare mode."""
        if not self.is_enabled() or graded_rgb is None:
            return None, None, "", ""
        mode = self.get_compare_mode()
        if mode == "off":
            return None, None, "", ""
        if mode == "original_vs_a":
            right = self.apply_lut_a(graded_rgb)
            return graded_rgb, right, "Original", (self.lut_a_combo.currentText() + f" ({self.get_strength_a():.2f})")
        if mode == "a_vs_b":
            left = self.apply_lut_a(graded_rgb)
            right = self.apply_lut_b(graded_rgb)
            return left, right, (self.lut_a_combo.currentText() + f" ({self.get_strength_a():.2f})"), (self.lut_b_combo.currentText() + f" ({self.get_strength_b():.2f})")
        return None, None, "", ""


# ══════════════════════════════════════════════════════════════════════════════
# VISUALIZATION PANEL WITH FULLSCREEN BUTTON
# ══════════════════════════════════════════════════════════════════════════════

class VisualizationPanel(QWidget):
    """Panel containing a visualization with fullscreen button."""
    
    def __init__(self, title, widget_class, parent=None):
        super().__init__(parent)
        self.title = title
        self.widget_class = widget_class
        self.current_data = None
        self.parent_window = parent
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Header with title and buttons
        header = QHBoxLayout()
        
        title_label = QLabel(title.upper())
        title_label.setStyleSheet(f"""
            color: {COLORS['text_dim']}; 
            font-size: 11px; 
            font-weight: 600;
            letter-spacing: 1px;
        """)
        header.addWidget(title_label)
        header.addStretch()
        
        # Reset view button
        reset_btn = QPushButton("⟲")
        reset_btn.setObjectName("fullscreen_btn")
        reset_btn.setToolTip("Reset view")
        reset_btn.clicked.connect(self._reset_view)
        header.addWidget(reset_btn)
        
        # Fullscreen button
        fullscreen_btn = QPushButton("⛶")
        fullscreen_btn.setObjectName("fullscreen_btn")
        fullscreen_btn.setToolTip("Fullscreen")
        fullscreen_btn.clicked.connect(self._open_fullscreen)
        header.addWidget(fullscreen_btn)
        
        layout.addLayout(header)
        
        # Main widget
        self.widget = widget_class(parent=self)
        layout.addWidget(self.widget)
        
        # Controls hint (waveform uses left-drag; others use right-drag)
        hint_text = getattr(widget_class, 'hint_text', 'Scroll: Zoom | Right-drag: Pan')
        hint = QLabel(hint_text)
        hint.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 9px;")
        hint.setAlignment(Qt.AlignRight)
        layout.addWidget(hint)
    
    def update_data(self, *args, **kwargs):
        """Store data and update widget."""
        self.current_data = (args, kwargs)
        self._update_widget(self.widget, *args, **kwargs)
    
    def _update_widget(self, widget, *args, **kwargs):
        """Update a widget with the current data."""
        if self.widget_class == WaveformWidget:
            widget.update_waveform(*args, **kwargs)
        elif self.widget_class == HistogramWidget:
            widget.update_histogram(*args, **kwargs)
        elif self.widget_class == ImagePreviewWidget:
            widget.update_image(*args, **kwargs)
    
    def _reset_view(self):
        self.widget.reset_view()
    
    def _open_fullscreen(self):
        if self.current_data is None:
            return
        
        dialog = FullscreenDialog(self.title, self.parent_window)
        
        # Create fullscreen version of widget
        fs_widget = self.widget_class(parent=dialog, fullscreen=True)
        
        # Toolbar with controls
        controls = QHBoxLayout()
        
        reset_btn = QPushButton("⟲ Reset View")
        reset_btn.clicked.connect(fs_widget.reset_view)
        controls.addWidget(reset_btn)
        
        controls.addStretch()
        
        # Info label
        info = QLabel("Scroll: Zoom | Right-drag: Pan | Esc: Close")
        info.setStyleSheet(f"color: {COLORS['text_dim']};")
        controls.addWidget(info)
        
        dialog.content_layout.addLayout(controls)
        dialog.content_layout.addWidget(fs_widget)
        
        # Update with current data
        args, kwargs = self.current_data
        self._update_widget(fs_widget, *args, **kwargs)
        
        dialog.showMaximized()
        dialog.exec_()


# ══════════════════════════════════════════════════════════════════════════════
# COLOR & ALPHA GRADING PANEL (sliders + spinboxes + color cues + reset)
# ══════════════════════════════════════════════════════════════════════════════

_SLIDER_RES = 1000  # slider range 0..1000 for smooth mapping


def _value_to_slider(val, low, high):
    if high <= low:
        return 0
    return int(_SLIDER_RES * (val - low) / (high - low))


def _slider_to_value(s, low, high):
    return low + (high - low) * (s / _SLIDER_RES)


class _GradingRow(QWidget):
    """One row: color strip, label, slider, spinbox, reset. Stays in sync and emits on change."""
    def __init__(self, label, low, high, default, tooltip, strip_color, parent=None):
        super().__init__(parent)
        self.low, self.high, self.default = low, high, default
        self._block = False
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(8)
        # Color strip (visual cue)
        strip = QFrame()
        strip.setFixedSize(6, 32)
        strip.setStyleSheet(f"background: {strip_color}; border-radius: 3px;")
        strip.setToolTip(tooltip)
        layout.addWidget(strip)
        # Label
        lbl = QLabel(label)
        lbl.setMinimumWidth(72)
        lbl.setStyleSheet(f"color: {COLORS['text']}; font-size: 12px; font-weight: 500;")
        lbl.setToolTip(tooltip)
        layout.addWidget(lbl)
        # Slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, _SLIDER_RES)
        self.slider.setValue(_value_to_slider(default, low, high))
        self.slider.setMinimumHeight(24)
        self.slider.valueChanged.connect(self._on_slider)
        layout.addWidget(self.slider, stretch=1)
        # Spinbox
        self.spin = QDoubleSpinBox()
        self.spin.setRange(low, high)
        self.spin.setValue(default)
        self.spin.setDecimals(2)
        self.spin.setSingleStep(0.1)
        self.spin.setMinimumWidth(56)
        self.spin.setMaximumWidth(64)
        self.spin.valueChanged.connect(self._on_spin)
        layout.addWidget(self.spin)
        # Reset
        self.reset_btn = QPushButton("↺")
        self.reset_btn.setFixedSize(28, 28)
        self.reset_btn.setToolTip("Reset to default")
        self.reset_btn.clicked.connect(self._reset)
        layout.addWidget(self.reset_btn)
        self.changed_callback = None

    def _on_slider(self, val):
        if self._block:
            return
        self._block = True
        v = _slider_to_value(val, self.low, self.high)
        self.spin.setValue(round(v, 2))
        self._block = False
        if self.changed_callback:
            self.changed_callback()

    def _on_spin(self, val):
        if self._block:
            return
        self._block = True
        self.slider.setValue(_value_to_slider(val, self.low, self.high))
        self._block = False
        if self.changed_callback:
            self.changed_callback()

    def _reset(self):
        self._block = True
        self.spin.setValue(self.default)
        self.slider.setValue(_value_to_slider(self.default, self.low, self.high))
        self._block = False
        if self.changed_callback:
            self.changed_callback()

    def value(self):
        return self.spin.value()


class GradingPanel(QWidget):
    """User-friendly color & alpha grading: sliders, spinboxes, color strips, tooltips, reset."""
    grading_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(STYLESHEET)
        self.setMinimumWidth(260)
        self.setMaximumWidth(340)
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        # —— Color ——
        color_grp = QGroupBox("Color")
        color_grp.setStyleSheet("QGroupBox { font-weight: 600; }")
        color_layout = QVBoxLayout(color_grp)
        color_layout.setSpacing(0)
        self.exposure_row = _GradingRow(
            "Exposure", -3.0, 3.0, 0.0,
            "Overall brightness in stops. +1 = 2× brighter.",
            "qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #1a1a1a, stop:1 #e8e8e8)",
            self,
        )
        self.exposure_row.changed_callback = self._emit_changed
        color_layout.addWidget(self.exposure_row)
        self.gamma_row = _GradingRow(
            "Gamma", 0.5, 4.0, 2.2,
            "Midtone curve. Lower = brighter midtones, higher = more contrast.",
            "#606060",
            self,
        )
        self.gamma_row.changed_callback = self._emit_changed
        color_layout.addWidget(self.gamma_row)
        self.lift_row = _GradingRow(
            "Lift", -0.5, 0.5, 0.0,
            "Shadow level. Add or subtract from blacks.",
            "#1a1a1a",
            self,
        )
        self.lift_row.changed_callback = self._emit_changed
        color_layout.addWidget(self.lift_row)
        self.gain_row = _GradingRow(
            "Gain", 0.1, 5.0, 1.0,
            "Highlight multiplier. Brightens or darkens highlights.",
            "#c0c0c0",
            self,
        )
        self.gain_row.changed_callback = self._emit_changed
        color_layout.addWidget(self.gain_row)
        self.saturation_row = _GradingRow(
            "Saturation", 0.0, 3.0, 1.0,
            "Chroma intensity. 0 = grayscale, 1 = unchanged, >1 = more vivid.",
            COLORS['accent'],
            self,
        )
        self.saturation_row.changed_callback = self._emit_changed
        color_layout.addWidget(self.saturation_row)
        layout.addWidget(color_grp)
        # —— Alpha ——
        alpha_grp = QGroupBox("Alpha")
        alpha_grp.setStyleSheet("QGroupBox { font-weight: 600; }")
        alpha_layout = QVBoxLayout(alpha_grp)
        self.alpha_row = _GradingRow(
            "Alpha", 0.0, 3.0, 1.0,
            "Scale the alpha channel. 0 = fully transparent, 1 = unchanged.",
            "qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #444, stop:0.5 #888, stop:1 #444)",
            self,
        )
        self.alpha_row.changed_callback = self._emit_changed
        alpha_layout.addWidget(self.alpha_row)
        layout.addWidget(alpha_grp)
        # Reset all
        reset_all = QPushButton("Reset all")
        reset_all.setToolTip("Reset all controls to default")
        reset_all.clicked.connect(self._reset_all)
        layout.addWidget(reset_all)
        layout.addStretch()

    def _emit_changed(self):
        self.grading_changed.emit()

    def _reset_all(self):
        self.exposure_row._reset()
        self.gamma_row._reset()
        self.lift_row._reset()
        self.gain_row._reset()
        self.saturation_row._reset()
        self.alpha_row._reset()
        self.grading_changed.emit()

    def get_grading(self):
        return {
            "exposure": self.exposure_row.value(),
            "gamma": self.gamma_row.value(),
            "lift": self.lift_row.value(),
            "gain": self.gain_row.value(),
            "saturation": self.saturation_row.value(),
            "alpha_scale": self.alpha_row.value(),
        }


# ══════════════════════════════════════════════════════════════════════════════
# SEQUENCE PLAYBACK TAB (EXR folder playback; inspired by Grizzly Peak 3D / DJV)
# ══════════════════════════════════════════════════════════════════════════════

def _natural_sort_key(s):
    """Sort key for frame names (e.g. frame_001.exr, frame_002.exr)."""
    return [int(x) if x.isdigit() else x.lower() for x in re.split(r'(\d+)', s)]


class SequencePlaybackTab(QWidget):
    """Load a folder of EXR frames and play them back. Keeps Analyzer look and feel."""
    
    _CACHE_MAX = 15  # max cached EXR frames to keep playback responsive

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(STYLESHEET)
        self.frame_paths = []
        self.current_index = 0
        self.playing = False
        self._play_timer = QTimer(self)
        self._play_timer.timeout.connect(self._on_play_tick)
        self._fps = 24
        self._frame_cache = {}  # path -> img (LRU by insertion order, bounded)
        self._cache_order = []  # list of path in order added
        self._grading = {}
        self._setup_ui()
    
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)
        splitter = QSplitter(Qt.Horizontal)
        # Left: toolbar + image + playback
        left = QWidget()
        layout = QVBoxLayout(left)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        toolbar = QHBoxLayout()
        load_btn = QPushButton("Load EXR folder")
        load_btn.clicked.connect(self._load_folder)
        toolbar.addWidget(load_btn)
        self.path_label = QLabel("No folder loaded")
        self.path_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 12px;")
        self.path_label.setMinimumWidth(200)
        toolbar.addWidget(self.path_label)
        self.count_label = QLabel("0 frames")
        self.count_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 12px;")
        toolbar.addWidget(self.count_label)
        self.export_btn = QPushButton("Export to ProRes / Cinema / MP4…")
        self.export_btn.clicked.connect(self._export_sequence)
        self.export_btn.setEnabled(False)
        toolbar.addWidget(self.export_btn)
        toolbar.addStretch()
        link = QLabel('<a href="https://github.com/grizzlypeak3d/djv" style="color: %s;">DJV — pro playback (Grizzly Peak 3D)</a>' % COLORS['accent'])
        link.setOpenExternalLinks(True)
        link.setStyleSheet(f"font-size: 11px;")
        toolbar.addWidget(link)
        layout.addLayout(toolbar)
        self.preview_stack = QStackedWidget()
        self.image_panel = VisualizationPanel("Sequence Preview", ImagePreviewWidget, self)
        self.preview_stack.addWidget(self.image_panel)
        self.compare_widget = SplitComparisonWidget(self)
        self.preview_stack.addWidget(self.compare_widget)
        layout.addWidget(self.preview_stack, stretch=1)
        controls = QHBoxLayout()
        self.play_btn = QPushButton("▶ Play")
        self.play_btn.clicked.connect(self._toggle_play)
        self.play_btn.setEnabled(False)
        controls.addWidget(self.play_btn)
        self.frame_slider = QSlider(Qt.Horizontal)
        self.frame_slider.setMinimum(0)
        self.frame_slider.setMaximum(0)
        self.frame_slider.valueChanged.connect(self._on_slider_changed)
        self.frame_slider.setMinimumWidth(300)
        controls.addWidget(self.frame_slider)
        self.frame_spin = QSpinBox()
        self.frame_spin.setMinimum(0)
        self.frame_spin.setMaximum(0)
        self.frame_spin.valueChanged.connect(self._on_spin_changed)
        self.frame_spin.setPrefix("Frame ")
        controls.addWidget(self.frame_spin)
        controls.addWidget(QLabel("FPS"))
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 120)
        self.fps_spin.setValue(24)
        self.fps_spin.valueChanged.connect(self._on_fps_changed)
        controls.addWidget(self.fps_spin)
        controls.addStretch()
        layout.addLayout(controls)
        splitter.addWidget(left)
        right_side = QWidget()
        right_layout = QVBoxLayout(right_side)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.grading_panel = GradingPanel(self)
        self.grading_panel.grading_changed.connect(self._on_grading_changed)
        right_layout.addWidget(self.grading_panel)
        self.lut_panel = LUTPanel(self)
        self.lut_panel.lut_changed.connect(self._on_lut_changed)
        right_layout.addWidget(self.lut_panel)
        right_layout.addStretch()
        splitter.addWidget(right_side)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        main_layout.addWidget(splitter)
        self._grading = self.grading_panel.get_grading()

    def _on_grading_changed(self):
        self._grading = self.grading_panel.get_grading()
        self._show_frame_at(self.current_index)

    def _on_lut_changed(self):
        self._show_frame_at(self.current_index)
    
    def _load_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select folder of EXR frames", "")
        if not folder:
            return
        paths = []
        for name in os.listdir(folder):
            if name.lower().endswith('.exr'):
                paths.append(os.path.join(folder, name))
        paths.sort(key=lambda p: _natural_sort_key(os.path.basename(p)))
        self.frame_paths = paths
        self.current_index = 0
        self.playing = False
        self._play_timer.stop()
        n = len(paths)
        self._frame_cache.clear()
        self._cache_order.clear()
        self.path_label.setText(os.path.basename(folder) or folder)
        self._update_count_label()
        self.frame_slider.setMaximum(max(0, n - 1))
        self.frame_spin.setMaximum(max(0, n - 1))
        self.play_btn.setEnabled(n > 0)
        self.export_btn.setEnabled(n > 0)
        if n > 0:
            self._show_frame_at(self.current_index)
        else:
            self.preview_stack.setCurrentIndex(0)
            self.image_panel.update_data(img_data=None, exposure=0.0)
    
    def _toggle_play(self):
        if not self.frame_paths:
            return
        self.playing = not self.playing
        self.play_btn.setText("⏸ Pause" if self.playing else "▶ Play")
        if self.playing:
            self._play_timer.start(int(1000 / self._fps))
        else:
            self._play_timer.stop()
    
    def _on_play_tick(self):
        if not self.frame_paths:
            return
        self.current_index = (self.current_index + 1) % len(self.frame_paths)
        self.frame_slider.blockSignals(True)
        self.frame_spin.blockSignals(True)
        self.frame_slider.setValue(self.current_index)
        self.frame_spin.setValue(self.current_index)
        self.frame_slider.blockSignals(False)
        self.frame_spin.blockSignals(False)
        self._show_frame_at(self.current_index)
    
    def _on_slider_changed(self, value):
        self.current_index = value
        self.frame_spin.blockSignals(True)
        self.frame_spin.setValue(value)
        self.frame_spin.blockSignals(False)
        self._show_frame_at(self.current_index)
    
    def _on_spin_changed(self, value):
        self.current_index = value
        self.frame_slider.blockSignals(True)
        self.frame_slider.setValue(value)
        self.frame_slider.blockSignals(False)
        self._show_frame_at(self.current_index)
    
    def _on_fps_changed(self, value):
        self._fps = value
        self._update_count_label()
        if self.playing:
            self._play_timer.setInterval(int(1000 / self._fps))

    def _update_count_label(self):
        """Update count label to show frames and duration at current FPS."""
        n = len(self.frame_paths)
        if n == 0:
            self.count_label.setText("0 frames")
            return
        dur = n / self._fps
        self.count_label.setText(f"{n} frames · {dur:.1f} s at {self._fps} fps")

    def _show_frame_at(self, index):
        if not self.frame_paths or index < 0 or index >= len(self.frame_paths):
            return
        path = self.frame_paths[index]
        # Use cache to avoid re-reading from disk every time (speeds up playback/scrub)
        img = self._frame_cache.get(path)
        if img is None:
            img = load_exr_frame(path)
            if img is not None:
                self._frame_cache[path] = img
                self._cache_order.append(path)
                while len(self._frame_cache) > self._CACHE_MAX and self._cache_order:
                    old = self._cache_order.pop(0)
                    self._frame_cache.pop(old, None)
        else:
            # LRU: move to end so this frame is evicted last
            if path in self._cache_order:
                self._cache_order.remove(path)
                self._cache_order.append(path)
        if img is not None:
            graded = apply_grading(img, **self._grading)
            compare_mode = self.lut_panel.get_compare_mode()
            if compare_mode != "off":
                left, right, lbl_left, lbl_right = self.lut_panel.get_left_right_for_compare(graded)
                self.preview_stack.setCurrentIndex(1)
                self.compare_widget.update_comparison(left, right, lbl_left, lbl_right)
            else:
                self.preview_stack.setCurrentIndex(0)
                display = self.lut_panel.apply_lut_a(graded) if self.lut_panel.get_lut_a_path() else graded
                self.image_panel.update_data(img_data=display, exposure=0.0)
        else:
            self.preview_stack.setCurrentIndex(0)
            self.image_panel.update_data(img_data=None, exposure=0.0)

    def _export_sequence(self):
        if not self.frame_paths:
            QMessageBox.warning(self, "Export", "Load an EXR folder first.")
            return
        if not _find_ffmpeg():
            QMessageBox.warning(
                self, "Export",
                "FFmpeg not found. Install FFmpeg and add it to PATH.\n\n"
                "See README and IT_PERMISSIONS_REQUEST.md for network/execution permissions."
            )
            return
        opts = ExportDialog(self, default_fps=self._fps)
        if opts.exec_() != QDialog.Accepted:
            return
        o = opts.get_options()
        ext = ".mov" if o["format_mov"] else ".mp4"
        first_name = os.path.splitext(os.path.basename(self.frame_paths[0]))[0] + ext
        filt = "QuickTime (*.mov);;MP4 (*.mp4);;All Files (*)" if o["format_mov"] else "MP4 (*.mp4);;QuickTime (*.mov);;All Files (*)"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export to ProRes / Cinema / MP4",
            first_name,
            filt
        )
        if not path:
            return
        if not path.lower().endswith((".mov", ".mp4")):
            path = path + ext
        progress = QProgressDialog("Exporting…", None, 0, 0, self)
        progress.setWindowTitle("Export")
        progress.setMinimumDuration(0)
        progress.show()
        grading = self._grading if hasattr(self, "_grading") else None
        self._export_worker = ExportWorker(
            self.frame_paths, path,
            o["format_mov"], o["codec_key"], o["scale_vf"], o["fps"],
            grading_params=grading,
        )
        def on_done(success, msg):
            progress.close()
            if success:
                QMessageBox.information(self, "Export", msg)
            else:
                QMessageBox.warning(self, "Export failed", msg[:2000])
        self._export_worker.finished_signal.connect(on_done)
        self._export_worker.start()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN WINDOW
# ══════════════════════════════════════════════════════════════════════════════

class EXRViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"EXR Analyzer — Cinema VFX Diagnostic Tool  v{__version__}")
        self.setMinimumSize(1400, 900)
        self.setStyleSheet(STYLESHEET)
        
        self.current_info = None
        self.compare_info = None

        self._setup_ui()
    
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)
        
        # Header (title only; tab-specific actions live in each tab)
        header = QHBoxLayout()
        title = QLabel("EXR ANALYZER")
        title.setFont(QFont('SF Pro Display', 24, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['text']}; letter-spacing: 2px;")
        header.addWidget(title)
        header.addStretch()
        main_layout.addLayout(header)
        
        # Tabs: Analyzer | Sequence
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {COLORS['border']}; border-radius: 8px; background: {COLORS['bg_card']}; }}
            QTabBar::tab {{ background: {COLORS['bg_light']}; color: {COLORS['text_dim']}; padding: 10px 20px; margin-right: 2px; }}
            QTabBar::tab:selected {{ background: {COLORS['bg_card']}; color: {COLORS['text']}; font-weight: 600; }}
            QTabBar::tab:hover:!selected {{ color: {COLORS['accent']}; }}
        """)
        
        # —— Tab 1: Analyzer (current single-file analysis)
        analyzer_page = QWidget()
        analyzer_layout = QVBoxLayout(analyzer_page)
        analyzer_layout.setContentsMargins(0, 0, 0, 0)
        analyzer_layout.setSpacing(16)
        
        analyzer_toolbar = QHBoxLayout()
        self.open_btn = QPushButton("Open EXR")
        self.open_btn.clicked.connect(self.open_file)
        analyzer_toolbar.addWidget(self.open_btn)
        self.compare_btn = QPushButton("Compare")
        self.compare_btn.clicked.connect(self.open_compare_file)
        self.compare_btn.setEnabled(False)
        analyzer_toolbar.addWidget(self.compare_btn)
        self.export_frame_btn = QPushButton("Export frame…")
        self.export_frame_btn.clicked.connect(self._export_current_frame)
        self.export_frame_btn.setEnabled(False)
        self.export_frame_btn.setToolTip("Export current EXR to ProRes / cinema format (1 frame)")
        analyzer_toolbar.addWidget(self.export_frame_btn)
        analyzer_toolbar.addStretch()
        analyzer_layout.addLayout(analyzer_toolbar)
        
        # Main content splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side: Visualizations
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)
        
        # Bento split: Image 50%, Waveform 25%, Histogram 25%
        self.image_panel = VisualizationPanel("Image Preview", ImagePreviewWidget, self)
        left_layout.addWidget(self.image_panel, stretch=2)
        
        self.waveform_panel = VisualizationPanel("Waveform", WaveformWidget, self)
        left_layout.addWidget(self.waveform_panel, stretch=1)
        
        self.histogram_panel = VisualizationPanel("Histogram", HistogramWidget, self)
        left_layout.addWidget(self.histogram_panel, stretch=1)
        
        splitter.addWidget(left_panel)
        
        # Right side: Stats only (no grading/LUT in Analyzer)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)
        
        # File info
        file_group = QGroupBox("FILE INFO")
        file_layout = QGridLayout(file_group)
        self.file_labels = {}
        file_fields = [
            ('Filename', 'filename'),
            ('Resolution', 'resolution'),
            ('File Size', 'filesize'),
            ('Compression', 'compression'),
            ('Bit Depth', 'native_type'),
            ('Color Space', 'colorspace'),
            ('Encoding', 'encoding'),
        ]
        for i, (label, key) in enumerate(file_fields):
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 11px;")
            val = QLabel("—")
            val.setStyleSheet(f"color: {COLORS['text']}; font-size: 13px; font-weight: 500;")
            file_layout.addWidget(lbl, i, 0)
            file_layout.addWidget(val, i, 1)
            self.file_labels[key] = val
        right_layout.addWidget(file_group)
        
        # Quality metrics
        quality_group = QGroupBox("QUALITY METRICS")
        quality_layout = QGridLayout(quality_group)
        self.quality_labels = {}
        quality_fields = [
            ('Range', 'range'),
            ('Above 1.0', 'above_1'),
            ('Unique Values', 'unique'),
            ('Midtone Step', 'step_ratio'),
            ('Effective Bits', 'eff_bits'),
            ('Quality', 'rating'),
        ]
        for i, (label, key) in enumerate(quality_fields):
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 11px;")
            val = QLabel("—")
            val.setStyleSheet(f"color: {COLORS['text']}; font-size: 13px; font-weight: 500;")
            quality_layout.addWidget(lbl, i, 0)
            quality_layout.addWidget(val, i, 1)
            self.quality_labels[key] = val
        right_layout.addWidget(quality_group)
        
        # Channel details
        channel_group = QGroupBox("CHANNEL ANALYSIS")
        channel_layout = QVBoxLayout(channel_group)
        self.channel_table = QTableWidget(3, 5)
        self.channel_table.setHorizontalHeaderLabels(['Channel', 'Min', 'Max', 'Mean', 'Unique'])
        self.channel_table.verticalHeader().setVisible(False)
        self.channel_table.setMaximumHeight(150)
        channel_layout.addWidget(self.channel_table)
        right_layout.addWidget(channel_group)
        
        # Comparison table
        self.compare_group = QGroupBox("COMPARISON")
        compare_layout = QVBoxLayout(self.compare_group)
        self.compare_table = QTableWidget(8, 3)
        self.compare_table.setHorizontalHeaderLabels(['Metric', 'File 1', 'File 2'])
        self.compare_table.verticalHeader().setVisible(False)
        compare_layout.addWidget(self.compare_table)
        self.compare_group.hide()
        right_layout.addWidget(self.compare_group)
        
        right_layout.addStretch()
        
        splitter.addWidget(right_panel)
        splitter.setSizes([900, 500])
        
        analyzer_layout.addWidget(splitter)
        self.tabs.addTab(analyzer_page, "Analyzer")
        
        # —— Tab 2: Sequence (folder load + playback)
        self.sequence_tab = SequencePlaybackTab(self)
        self.tabs.addTab(self.sequence_tab, "Sequence")
        
        main_layout.addWidget(self.tabs)
        
        # Status bar
        self.status = QLabel("Ready — Open an EXR file to analyze, or use Sequence tab to load a folder")
        self.status.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 11px; padding: 8px;")
        main_layout.addWidget(self.status)
    
    def open_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open EXR File", "", "EXR Files (*.exr);;All Files (*)"
        )
        if filepath:
            self.analyze_file(filepath)
    
    def open_compare_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open EXR to Compare", "", "EXR Files (*.exr);;All Files (*)"
        )
        if filepath:
            self.compare_info = analyze_exr(filepath)
            self.update_comparison()
    
    def analyze_file(self, filepath):
        self.status.setText(f"Analyzing {os.path.basename(filepath)}...")
        QApplication.processEvents()
        
        try:
            self.current_info = analyze_exr(filepath)
            self.update_display()
            self.compare_btn.setEnabled(True)
            self.export_frame_btn.setEnabled(True)
            self.status.setText(f"✓ Analyzed: {self.current_info['filename']}")
        except Exception as e:
            self.status.setText(f"✗ Error: {str(e)}")
    
    def update_display(self):
        info = self.current_info
        if not info:
            return
        
        # Update file info
        self.file_labels['filename'].setText(info['filename'])
        self.file_labels['resolution'].setText(f"{info['width']} × {info['height']}")
        self.file_labels['filesize'].setText(f"{info['filesize_mb']:.1f} MB")
        self.file_labels['compression'].setText(info['compression'])
        self.file_labels['native_type'].setText(info['native_type'])
        self.file_labels['colorspace'].setText(info['colorspace'])
        self.file_labels['encoding'].setText(info['encoding'])
        
        # Update quality metrics
        self.quality_labels['range'].setText(f"{info['range_min']:.3f} — {info['range_max']:.3f}")
        self.quality_labels['above_1'].setText(f"{info['above_1_pct']:.1f}%")
        self.quality_labels['unique'].setText(f"{info['avg_unique']:.0f}")
        self.quality_labels['step_ratio'].setText(f"{info['avg_step_ratio']:.1f}× finer than 8-bit")
        self.quality_labels['eff_bits'].setText(f"~{info['eff_bits']:.1f} bits")
        self.quality_labels['rating'].setText(info['rating'])
        
        # Color code rating
        if "★★★★★" in info['rating']:
            color = COLORS['accent']
        elif "★★★★" in info['rating']:
            color = COLORS['accent']
        elif "★★★" in info['rating']:
            color = COLORS['warning']
        else:
            color = COLORS['error']
        self.quality_labels['rating'].setStyleSheet(f"color: {color}; font-size: 13px; font-weight: 600;")
        
        # Update channel table
        self.channel_table.setRowCount(3)
        for i, ch in enumerate(['R', 'G', 'B']):
            if ch in info['results']:
                r = info['results'][ch]
                self.channel_table.setItem(i, 0, QTableWidgetItem(ch))
                self.channel_table.setItem(i, 1, QTableWidgetItem(f"{r['min']:.4f}"))
                self.channel_table.setItem(i, 2, QTableWidgetItem(f"{r['max']:.4f}"))
                self.channel_table.setItem(i, 3, QTableWidgetItem(f"{r['mean']:.4f}"))
                self.channel_table.setItem(i, 4, QTableWidgetItem(f"{r['unique_count']}"))
        
        # Update visualizations (raw image, no grading/LUT in Analyzer)
        self.image_panel.update_data(info['img_data'])
        self.waveform_panel.update_data(info['img_data'])
        self.histogram_panel.update_data(info)
    
    def update_comparison(self):
        if not self.current_info or not self.compare_info:
            return
        
        self.compare_group.show()
        a, b = self.current_info, self.compare_info
        
        rows = [
            ('Filename', a['filename'], b['filename']),
            ('File Size', f"{a['filesize_mb']:.1f} MB", f"{b['filesize_mb']:.1f} MB"),
            ('Compression', a['compression'], b['compression']),
            ('Range', f"{a['range_min']:.3f} - {a['range_max']:.3f}", f"{b['range_min']:.3f} - {b['range_max']:.3f}"),
            ('Above 1.0', f"{a['above_1_pct']:.1f}%", f"{b['above_1_pct']:.1f}%"),
            ('Unique Values', f"{a['avg_unique']:.0f}", f"{b['avg_unique']:.0f}"),
            ('Midtone Step', f"{a['avg_step_ratio']:.1f}×", f"{b['avg_step_ratio']:.1f}×"),
            ('Effective Bits', f"~{a['eff_bits']:.1f}", f"~{b['eff_bits']:.1f}"),
        ]
        
        self.compare_table.setRowCount(len(rows))
        for i, (label, va, vb) in enumerate(rows):
            self.compare_table.setItem(i, 0, QTableWidgetItem(label))
            self.compare_table.setItem(i, 1, QTableWidgetItem(va))
            self.compare_table.setItem(i, 2, QTableWidgetItem(vb))
        
        diff = a['eff_bits'] - b['eff_bits']
        if abs(diff) > 0.2:
            winner_msg = f"{'File 1' if diff > 0 else 'File 2'} has ~{abs(diff):.1f} more effective bits"
            self.status.setText(f"Comparison: {winner_msg}")

    def _export_current_frame(self):
        """Export current Analyzer image to ProRes/cinema/MP4 (1 frame)."""
        if not self.current_info or self.current_info.get("img_data") is None:
            QMessageBox.warning(self, "Export", "Open an EXR file first.")
            return
        if not _find_ffmpeg():
            QMessageBox.warning(
                self, "Export",
                "FFmpeg not found. Install FFmpeg and add it to PATH.\n\n"
                "See README and IT_PERMISSIONS_REQUEST.md for permissions."
            )
            return
        opts = ExportDialog(self, default_fps=24)
        if opts.exec_() != QDialog.Accepted:
            return
        o = opts.get_options()
        ext = ".mov" if o["format_mov"] else ".mp4"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export frame to ProRes / Cinema / MP4",
            "frame" + ext,
            "QuickTime (*.mov);;MP4 (*.mp4);;All Files (*)"
        )
        if not path:
            return
        if not path.lower().endswith((".mov", ".mp4")):
            path = path + ext
        import tempfile
        fd, temp_exr = tempfile.mkstemp(suffix=".exr")
        os.close(fd)
        img = self.current_info["img_data"]
        if not write_exr_frame(temp_exr, img):
            try:
                os.unlink(temp_exr)
            except Exception:
                pass
            QMessageBox.warning(self, "Export", "Could not write temporary EXR.")
            return
        progress = QProgressDialog("Exporting…", None, 0, 0, self)
        progress.setWindowTitle("Export")
        progress.setMinimumDuration(0)
        progress.show()
        worker = ExportWorker(
            [temp_exr], path,
            o["format_mov"], o["codec_key"], o["scale_vf"], o["fps"],
        )
        def on_done(success, msg):
            try:
                os.unlink(temp_exr)
            except Exception:
                pass
            progress.close()
            if success:
                QMessageBox.information(self, "Export", msg)
            else:
                QMessageBox.warning(self, "Export failed", msg[:2000])
        worker.finished_signal.connect(on_done)
        worker.start()
        self._export_worker = worker


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = EXRViewer()
    window.show()
    
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        window.analyze_file(sys.argv[1])
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except BaseException as e:
        tb = traceback.format_exc()
        _show_error_win(
            "EXR Analyzer failed to start:\n\n" + tb + "\n\n"
            "Please ensure all requirements are installed:\n"
            "  pip install -r requirements.txt\n\n"
            "On Windows, use run_windows.bat to keep the window open. "
            "Full error is also saved to exr_analyzer_crash.log",
            "EXR Analyzer - Error",
        )
        sys.exit(1)
