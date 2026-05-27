# OrbitalViewer

[![Bilibili](https://img.shields.io/badge/Bilibili-Tutorial-00A1D6?style=flat&logo=bilibili)](https://www.bilibili.com/video/BV1spGC68Eej/)

**OrbitalViewer** — a PyQt5 GUI that streamlines the Multiwfn → VMD → Tachyon workflow for molecular orbital visualization.

> 分子轨道等值面可视化工具，PyQt5 重写，一键串联 Multiwfn + VMD + Tachyon。

## Features

- **fchk → cube** via Multiwfn
- **VMD live preview** of orbital isosurfaces (multi-orbital support)
- **Tachyon ray-tracing** export to high-res BMP/PNG
- **Real-time isovalue & opacity sliders** — adjust while watching VMD update live
- **11 built-in rendering styles** from vcube2.0 (Zhong Cheng)
- **Hide hydrogen atoms** with optional index exclusion
- **Dashed bond drawing tool** for annotating interactions
- **Batch processing** — drop a folder and walk away
- **Bilingual UI** (Chinese: `orbital_viewer_zh.py` / English: `orbital_viewer.py`)

## Video Tutorial

> 🎬 [Bilibili: OrbitalViewer 大升级！PyQt5 重写](https://www.bilibili.com/video/BV1spGC68Eej/)

## Download

Pre-built executable (no Python required):

📥 **[OrbitalViewer.exe](https://cnb.cool/chem311/OrbitalViewer/-/raw/main/dist/OrbitalViewer.exe)** (~58 MB)

## Dependencies

| Dependency | Role | Install |
|------------|------|---------|
| Python 3.8+ | Runtime | — |
| PyQt5 | GUI | `pip install PyQt5` |
| [Multiwfn](http://sobereva.com/multiwfn/) | fchk → cube | Download & configure path |
| [VMD](https://www.ks.uiuc.edu/Research/vmd/) | 3D preview + Tachyon | Install & configure path |
| Tachyon | Ray tracing | Bundled with VMD |

## Quick Start

### 1. Install Python dependency

```bash
pip install PyQt5
```

### 2. Configure tool paths

Edit `fchk_orbital.ini`:

```ini
[paths]
multiwfn = E:\Multiwfn_2026.4.10_bin_Win64\Multiwfn.exe
vmd = C:\Program Files (x86)\University of Illinois\VMD\vmd.exe
tachyon = C:\Program Files (x86)\University of Illinois\VMD\tachyon_WIN32.exe
```

### 3. Run

```bash
# Chinese UI
python orbital_viewer_zh.py

# English UI
python orbital_viewer.py
```

### 4. Build exe (optional)

```bash
pyinstaller orbital_viewer_zh.spec
```

## CLI Mode

```bash
# Batch process a folder, HOMO + LUMO, isovalue 0.05
python orbital_viewer.py folder/ --mo h,l --iso 0.05
```

## Project Structure

```
├── orbital_viewer.py       # English GUI
├── orbital_viewer_zh.py    # Chinese GUI
├── fchk_orbital.py         # Backend (cube gen, VMD control, rendering)
├── fchk_orbital.ini        # External tool path configuration
├── orbital_viewer_zh.spec  # PyInstaller spec
├── dist/OrbitalViewer.exe  # Pre-built executable
└── README.md
```

## License

Academic use.
