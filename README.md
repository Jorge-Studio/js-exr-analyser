# EXR Analyzer — Cinema VFX Pipeline Diagnostic Tool

A professional GUI application for analyzing EXR files, measuring bit depth quality, and visualizing waveforms and histograms. Built for the [js-exr-upbitrate](https://github.com/Jorge-Studio/js-exr-analyser) ComfyUI ecosystem.

![EXR Analyzer Screenshot](screenshot.png)

---

## Features

- **Bit depth analysis** — Counts unique values to determine effective bit depth
- **Quality rating** — Cinema-grade (5★) to 8-bit equivalent (1★) ratings
- **Waveform** — DaVinci Resolve–style RGB waveform (envelope or full-spectrum), with R/G/B toggles
- **Histogram** — RGB histogram with zoom/pan and R/G/B channel toggles
- **Image preview** — Tone-mapped HDR preview with zoom/pan
- **File comparison** — Compare two EXR files side-by-side
- **Color space detection** — ACES, Rec.709, Rec.2020, DCI-P3
- **Encoding detection** — Linear vs Log (e.g. ACEScct/LogC)
- **Constrained axes** — Waveform and histogram zoom/pan limited to data range + 10% for readable navigation

---

## Quality metrics

| Rating | Effective bits | Unique values | Use case |
|--------|----------------|---------------|----------|
| ★★★★★ Cinema-grade | 13+ bits | 8,000+ | Professional VFX |
| ★★★★☆ Good | 11.5–13 bits | 3,000–8,000 | High-end production |
| ★★★☆☆ Acceptable | 10–11.5 bits | 1,000–3,000 | Standard production |
| ★★☆☆☆ Poor | 8.5–10 bits | 360–1,000 | Limited grading |
| ★☆☆☆☆ 8-bit equivalent | <8.5 bits | <360 | Not recommended |

---

## Requirements

- **Python 3.8+**
- **pip**

---

## Installation

### Windows

1. **Quick start (recommended)**  
   Double-click **`run_windows.bat`**.  
   It will create a venv if needed, install dependencies, and start the app. On first run or after updates, allow network so `pip` can install packages.

2. **Manual**
   ```cmd
   cd path\to\exr_analyzer
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   python exr_analyzer.py
   ```

### macOS / Linux

1. **Quick start**
   ```bash
   chmod +x run_mac.command   # or run_linux.sh on Linux
   ./run_mac.command
   ```
   Or double-click `run_mac.command` in Finder (macOS).

2. **Manual**
   ```bash
   cd path/to/exr_analyzer
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python exr_analyzer.py
   ```

The app also attempts to install requirements from `requirements.txt` on startup if something is missing (helpful on Windows when the batch file didn’t run in a venv).

---

## Usage

### Launch

```bash
# No arguments — use "Open EXR" in the app
python exr_analyzer.py

# Open a file directly
python exr_analyzer.py /path/to/your/file.exr
```

### Main actions

1. **Open EXR** — Load an EXR; file info, quality metrics, waveform, and histogram update.
2. **Compare** — Load a second EXR and compare metrics in the Comparison panel.
3. **Waveform** — Toggle **FULL waveform** for full-spectrum scatter; use **R**, **G**, **B** to show/hide channels.
4. **Histogram** — Use **R**, **G**, **B** to show/hide channels. Y-axis is capped so a large peak at 1.0 doesn’t squash the rest of the data.
5. **Zoom / pan** — Scroll to zoom, right-drag (or middle-drag) to pan on Image, Waveform, and Histogram. **Waveform** uses left-drag to pan (pyqtgraph). Axes are constrained to data ± 10%.
6. **Reset view** — **⟲** on each panel resets zoom/pan.
7. **Fullscreen** — **⛶** opens that panel in a separate window; **Esc** or **✕** closes it.

### Layout

- **Left:** Image preview (50%), Waveform (25%), Histogram (25%). Drag the vertical divider to resize.
- **Right:** File info, quality metrics, channel analysis, and (when comparing) comparison table.

---

## Controls summary

| Where | Action |
|-------|--------|
| **Image / Histogram** | Scroll = zoom, **right-drag** = pan |
| **Waveform** | Scroll = zoom, **left-drag** = pan |
| **All panels** | ⟲ = reset view, ⛶ = fullscreen |
| **Fullscreen** | Esc or ✕ = close |

---

## Understanding the results

- **Range** — Min–max value in the file (0–1 ≈ SDR; >1 includes HDR).
- **Above 1.0** — % of pixels with value > 1.
- **Unique values** — Count of distinct values (higher = better).
- **Midtone step** — Finer than 8-bit in midtones (higher = better).
- **Effective bits** — Estimated bit depth from unique values.

---

## Troubleshooting

### Windows: app opens and closes immediately

- Run **`run_windows.bat`** from a folder that contains `exr_analyzer.py` and `requirements.txt`.
- If an error box appears, follow the message (e.g. run `pip install -r requirements.txt` in the same folder, with the same Python).
- Ensure **Python 3.8+** is installed and “Add Python to PATH” was checked. Install from [python.org](https://www.python.org/downloads/).

### "OpenEXR not found" or other missing module

```cmd
pip install -r requirements.txt
```

If OpenEXR still fails, try:

```cmd
pip install --upgrade pip
pip install OpenEXR
```

### macOS: "No module named PyQt5"

```bash
pip install PyQt5
# or
pip install -r requirements.txt
```

### Linux: missing system libs

```bash
# Ubuntu/Debian
sudo apt-get install python3-pyqt5 libopenexr-dev

# Fedora
sudo dnf install python3-qt5 openexr-devel
```

### "Fontconfig error: No writable cache directories"

Usually harmless; the app should still run.

---

## Project structure

```
exr_analyzer_6Feb/
├── exr_analyzer.py    # Main application
├── requirements.txt   # Python dependencies
├── run_windows.bat    # Windows launcher
├── run_mac.command    # macOS launcher
├── run_linux.sh       # Linux launcher
├── README.md          # This file
├── USER_CONTROLS.md   # Detailed GUI reference
├── UI_IMPROVEMENT_GUIDE.md
└── WAVEFORM_LAG_ANALYSIS.md
```

---

## License

MIT License — free for commercial and personal use.

---

## Credits

Built for the **js-exr-upbitrate** ComfyUI node package.  
Repository: [Jorge-Studio/js-exr-analyser](https://github.com/Jorge-Studio/js-exr-analyser).
