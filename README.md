**English** | [简体中文](./README_zh.md)

<p align="center">
  <img src="https://img.shields.io/badge/version-5.3-blue.svg" alt="Version 5.3">
  <img src="https://img.shields.io/badge/python-3.8+-green.svg" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/license-MIT-orange.svg" alt="MIT License">
</p>

<h1 align="center">OrbitalViewer</h1>

<p align="center">
  <b>From fchk to publication-quality orbital figures in two minutes — Multiwfn → VMD → Tachyon, all in one click.</b>
  <br>
  <sub>Hou Cheng Research Group · Guangxi Normal University</sub>
</p>

---

## Why OrbitalViewer?

Traditional orbital visualization workflows require manually running Multiwfn to generate cube files, then loading into VMD, tweaking parameters, and rendering — tedious and error-prone. OrbitalViewer automates the entire pipeline with an intuitive GUI and 30+ built-in rendering styles.

| | Traditional | OrbitalViewer |
|---|---|---|
| Cube generation | Manual command-line | Double-click to generate |
| VMD preview | Manual load & tune | Auto-load with real-time sliders |
| Rendering | Manual light/material tweaks | Dropdown style picker, one-click render |
| Batch processing | Repeat per file | Drag folder, fully automatic |
| Bilingual | — | Chinese/English in-app switch |

<p align="center">
  <i>📸 Drag fchk → double-click orbital → pick style → render. That's it.</i>
  <br>
  <!-- TODO: Add screenshots here -->
  <!-- <img src="docs/screenshot.png" width="800" alt="Screenshot"> -->
</p>

---

## Features

### 🧬 Smart File Loading
- **Drag & drop** — Supports `.fchk`, `.log`, `.out`, `.cub`, `.cube`, `.xyz` files with automatic format detection
- **Auto bonding** — Chemical bonds computed and rendered in a 2D preview canvas

### 📊 Orbital Browser
- **Dual-tab layout** — Open-shell α/β electrons auto-separated into adjacent tabs
- **Occupation visualization** — ⬆️⬇️ doubly occupied / ⬆️ α single / ⬇️ β single / ⬜ empty
- **Full information** — Orbital index, energy (a.u.), energy (eV), occupation number
- **Double-click to generate** — Automatically run Multiwfn to produce cube and send to VMD

### 🎬 Real-time VMD Preview
- **Isosurface slider** — Drag to adjust isovalue in VMD in real time (0.01–0.10)
- **Opacity control** — Independent adjustment for positive/negative isosurfaces
- **Multi-orbital display** — Load multiple orbitals simultaneously with independent colors
- **One-click hide hydrogens** — Highlight heavy-atom backbone, with option to keep selected H

### 🎨 30+ Built-in Rendering Styles

| Category | Styles | Count |
|----------|--------|:---:|
| **vcube2.0 (Zhong Cheng)** | sob-art, ao-shiny, ao-chalky, white-green, white-red, morandi-blue, morandi-green, morandi-orange, morandi-red, vmwfn0, vmwfn1, IQmol | 12 |
| **IboView Style** | iboview-crystal, iboview-dark, iboview-green-pink, iboview-purple-blue, iboview-cyan-yellow, iboview-orange-teal, iboview-rainbow | 7 |
| **Original Designs** | aurora-teal, midnight-gold, lavender-mint, sunset-fire, ocean-depth, rose-quartz, forest-emerald, neon-cyber, cherry-blossom, graphite-ink, lakers, blood-orange, Gaussview | 13+ |

### 🖼️ Tachyon Ray Tracing
- **4 render modes** — Solid, CPK, Sob-Multi, Sob-Art
- **High resolution** — BMP/PNG output up to 3000+ pixels
- **Transparent background** — Optional for post-processing
- **Shadow control** — Toggle shadows and ambient occlusion (AO)
- **Custom Tachyon path** — Choose any Tachyon binary version

### ✏️ Dashed Bond Tool
- **One-click atom-pair locking** — Canvas and VMD synchronized dashed bonds
- **8 colors + 5 line styles** — Dots, dashes, cylinders, cones, segments; dropdown instant preview
- **Annotate hydrogen bonds and intermolecular interactions**

### 🔄 Advanced Overlay Mode
- Select two orbitals for simultaneous cube generation and overlay rendering
- Compare HOMO/LUMO or different isovalue thresholds side by side

### 📦 Batch Processing
- Drop a folder to process all fchk files automatically
- Command-line batch mode with customizable orbitals, styles, and resolution

### 🌐 Bilingual UI
- Chinese / English instant switch, no restart required
- Full coverage of all UI text and tooltips

### 📋 Runtime Log
- 16px monospace font, color-coded labels (`VMD` / `OK` / `ERR` / `GEN`)
- Timestamped, ready to copy and export

---

## Quick Start

### Requirements

| Component | Purpose | Installation |
|-----------|---------|-------------|
| Python 3.8+ | Runtime | [python.org](https://www.python.org/) |
| PyQt5 | GUI | `pip install PyQt5` |
| NumPy | Numerical computing | `pip install numpy` |
| [Multiwfn](http://sobereva.com/multiwfn/) | fchk → cube | Download & configure path |
| [VMD](https://www.ks.uiuc.edu/Research/vmd/) | 3D preview & rendering | Install & configure path |
| Tachyon | Ray tracing | Bundled with VMD |

### Installation

```bash
git clone https://github.com/houcheng-gxnu/OrbitalViewer.git
cd OrbitalViewer
pip install PyQt5 numpy
```

### Configure Tool Paths

On first launch, browse to each tool in the GUI settings, or manually edit `fchk_orbital.ini`:

```ini
[paths]
multiwfn = E:\Multiwfn_2026.4.10_bin_Win64\Multiwfn.exe
vmd      = C:\Program Files (x86)\University of Illinois\VMD\vmd.exe
tachyon  = C:\Program Files (x86)\University of Illinois\VMD\tachyon_WIN64.exe
```

> **Tip**: Both Multiwfn and VMD paths can be configured through the GUI settings dialog — configuration is auto-saved.

### Launch

```bash
# GUI mode (defaults to Chinese)
python main.py

# English UI — switch from menu: Language / 语言 → English
```

### Command-Line Mode

```bash
# Single file, HOMO, soba-recommended style
python main.py input.fchk --mo h --iso 0.05 --style sob-art

# Batch folder, HOMO + LUMO
python main.py ./fchk_folder/ --mo h,l --iso 0.05

# Custom orbitals, style, and high resolution
python main.py input.fchk --mo h-1,h,l,l+1 --iso 0.04 --style lakers --res 3000,2250

# Cube only, no render (useful for debugging)
python main.py ./folder/ --mo h --grid 3 --no-render
```

### Command-Line Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `input` | str | — | fchk file path or folder path |
| `--mo` | str | `h` | Orbital selection: `h` (HOMO), `l` (LUMO), `h-1` (HOMO-1), numeric index, comma-separated for multiples |
| `--iso` | float | `0.05` | Isosurface threshold value |
| `--grid` | int | `2` | Grid quality: 1=low, 2=medium, 3=high |
| `--style` | str | `sob-art` | Render style; see `STYLES` dict keys in `fchk_orbital.py` |
| `--res` | str | `2000,1500` | Output resolution as `width,height` |
| `--no-render` | flag | — | Only generate cube files, skip Tachyon rendering |
| `--out` | str | same as input | Output directory |

---

## Project Structure

```
OrbitalViewer/
├── main.py                # Entry point (GUI launcher + CLI batch)
├── main_window.py         # Main window (UI layout, signal/slot logic)
├── molcanvas.py           # 2D molecular structure canvas (Qt QPainter)
├── fchk_orbital.py        # Backend engine (cube gen, VMD control, Tachyon pipeline, 30+ styles)
├── fchk_parser.py         # fchk file parser (orbital energies, occupations)
├── orbital_viewer_lib.py  # Shared utility library
├── orbital_viewer_v53.py  # Legacy compatibility layer
├── workers.py             # QThread workers (async cube gen & render)
├── widgets.py             # Custom QSS widgets (sliders, combos, buttons)
├── dialogs.py             # Dialogs (settings, about, path config)
├── i18n.py                # Internationalization (Chinese/English dictionaries)
├── theme.py               # QSS theme stylesheet
├── OrbitalViewer.spec     # PyInstaller packaging config
└── README.md
```

---

## Build Standalone EXE

No Python required — ideal for distributing to non-technical users.

```bash
pip install pyinstaller
pyinstaller OrbitalViewer.spec --clean
```

Output: `dist/OrbitalViewer.exe` (single file, no console window).

---

## Acknowledgements

OrbitalViewer stands on the shoulders of giants:

- **[Multiwfn](http://sobereva.com/multiwfn/)** — Wavefunction analysis program by Prof. Tian Lu, with 40,000+ citations. OrbitalViewer uses it to generate cube files from fchk.
- **[vcube2.0](https://github.com/Zhong-Cheng-2020/vcube2.0)** — 11 beautiful VMD rendering configs by Zhong Cheng, which form the basis of most built-in styles.
- **[VMD](https://www.ks.uiuc.edu/Research/vmd/)** — Humphrey, W., Dalke, A. and Schulten, K., "VMD: Visual Molecular Dynamics", J. Molec. Graphics, 1996, 14, 33–38.
- **[Tachyon](http://jedi.ks.uiuc.edu/~johns/raytracer/)** — Stone, J. E., "An Efficient Library for Parallel Ray Tracing and Animation", M.Sc. Thesis, 1998.
- **Dashed bond drawing** — Based on Eming's `draw_bond` Tcl script from the KeinSci forum.

---

## Citation

If OrbitalViewer helps your research, please cite:

```bibtex
@software{OrbitalViewer2026,
  title        = {OrbitalViewer: A Molecular Orbital Isosurface Visualization Tool},
  author       = {Hou Cheng},
  year         = {2026},
  version      = {5.3},
  url          = {https://github.com/houcheng-gxnu/OrbitalViewer},
}
```

Please also cite the relevant tools listed in the Acknowledgements section.

See also [CITATION.cff](./CITATION.cff) and [CITATION.bib](./CITATION.bib).

---

## License

MIT License — see [LICENSE](./LICENSE) for details.

---

<p align="center">
  <sub>Made with ❤️ by Hou Cheng Research Group @ Guangxi Normal University</sub>
</p>
