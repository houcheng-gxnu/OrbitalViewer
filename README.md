# OrbitalViewer

[![Bilibili](https://img.shields.io/badge/Bilibili-Tutorial-00A1D6?style=flat&logo=bilibili)](https://www.bilibili.com/video/BV1V5Gm6pEGr/)

**OrbitalViewer** — a PyQt5 GUI that streamlines the Multiwfn → VMD → Tachyon workflow for molecular orbital visualization.

## Features

- **fchk → cube** via Multiwfn
- **VMD live preview** of orbital isosurfaces (multi-orbital support)
- **Tachyon ray-tracing** export to high-res BMP/PNG
- **Real-time isovalue & opacity sliders** — adjust while watching VMD update live
- **11 built-in rendering styles** from vcube2.0 (Zhong Cheng)
- **Hide hydrogen atoms** with optional index exclusion
- **Dashed bond drawing** for annotating interactions
- **Batch processing** — drop a folder and walk away
- **Bilingual UI** (Chinese / English)

## Video Tutorial

> 🎬 [OrbitalViewer: From fchk to Publication-Ready Image in 2 Minutes](https://www.bilibili.com/video/BV1V5Gm6pEGr/)

## Download

Pre-built executables (no Python required):

| Version | File |
|---------|------|
| Chinese | `OrbitalViewer_zh.exe` |
| English | `OrbitalViewer_en.exe` |

📁 **[Browse all downloads →](https://cnb.cool/chem311/OrbitalViewer/-/tree/main/dist)**

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
├── fchk_orbital.ini        # External tool path config
├── orbital_viewer_zh.spec  # PyInstaller spec
├── dist/
│   ├── OrbitalViewer_zh.exe  # Chinese pre-built
│   └── OrbitalViewer_en.exe  # English pre-built
└── README.md
```

## License

Academic use.

---

# OrbitalViewer（中文）

**OrbitalViewer** — 基于 PyQt5 的分子轨道等值面可视化工具，一键串联 Multiwfn → VMD → Tachyon 工作流。

## 功能

- **fchk → cube**：调用 Multiwfn 自动生成 cube 文件
- **VMD 实时预览**：多轨道同时显示，每轨道独立配色
- **Tachyon 光线追踪渲染**：输出高清 BMP/PNG
- **等值面 & 透明度滑块实时调节**：拖动滑块，VMD 中轨道面同步变化
- **11 种内置渲染风格**：来自 vcube2.0（钟成），一键切换
- **一键隐藏氢原子**：突出重原子骨架
- **虚线绘制工具**：标注氢键和分子间相互作用
- **批量处理**：拖入文件夹，自动批处理出图

## 视频教程

> 🎬 [OrbitalViewer: From fchk to Publication-Ready Image in 2 Minutes](https://www.bilibili.com/video/BV1V5Gm6pEGr/)

## 下载

提供预编译 exe，无需 Python：

| 版本 | 文件 |
|------|------|
| 中文版 | `OrbitalViewer_zh.exe` |
| 英文版 | `OrbitalViewer_en.exe` |

📁 **[浏览全部下载 →](https://cnb.cool/chem311/OrbitalViewer/-/tree/main/dist)**

## 协议

学术用途。
