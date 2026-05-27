# OrbitalViewer

[![Bilibili](https://img.shields.io/badge/Bilibili-视频教程-00A1D6?style=flat&logo=bilibili)](https://www.bilibili.com/video/BV1V5Gm6pEGr/)

**OrbitalViewer** — 基于 PyQt5 的分子轨道等值面可视化工具，一键串联 Multiwfn → VMD → Tachyon 工作流。

## 功能

- **fchk → cube**：调用 Multiwfn 自动生成 cube 文件
- **VMD 实时预览**：支持多轨道同时显示，每轨道独立配色
- **Tachyon 光线追踪渲染**：输出高清 BMP/PNG 图片
- **等值面 & 透明度滑块实时调节**：拖动滑块，VMD 中轨道面同步变化，丝滑流畅
- **11 种内置渲染风格**：来自 vcube2.0（钟成），一键切换
- **一键隐藏氢原子**：突出重原子骨架，支持指定保留编号
- **虚线绘制工具**：标注氢键和分子间相互作用，支持撤销和清除
- **批量处理**：拖入整个文件夹，自动批处理出图
- **双语界面**：中文版 `orbital_viewer_zh.py` / 英文版 `orbital_viewer.py`

## 视频教程

> 🎬 [OrbitalViewer: From fchk to Publication-Ready Image in 2 Minutes](https://www.bilibili.com/video/BV1V5Gm6pEGr/)

## 下载

提供预编译 exe，无需安装 Python 环境，双击即用：

| 版本 | 文件名 |
|------|--------|
| 中文版 | `OrbitalViewer_zh.exe` |
| 英文版 | `OrbitalViewer_en.exe` |

📁 **[浏览全部下载文件 →](https://cnb.cool/chem311/OrbitalViewer/-/tree/main/dist)**

## 依赖环境

| 依赖 | 用途 | 安装方式 |
|------|------|----------|
| Python 3.8+ | 运行环境 | — |
| PyQt5 | GUI 界面 | `pip install PyQt5` |
| [Multiwfn](http://sobereva.com/multiwfn/) | fchk → cube | 下载后配置路径 |
| [VMD](https://www.ks.uiuc.edu/Research/vmd/) | 3D 预览 + Tachyon | 安装后配置路径 |
| Tachyon | 光线追踪渲染 | VMD 自带 |

## 快速开始

### 1. 安装 Python 依赖

```bash
pip install PyQt5
```

### 2. 配置工具路径

编辑 `fchk_orbital.ini`：

```ini
[paths]
multiwfn = E:\Multiwfn_2026.4.10_bin_Win64\Multiwfn.exe
vmd = C:\Program Files (x86)\University of Illinois\VMD\vmd.exe
tachyon = C:\Program Files (x86)\University of Illinois\VMD\tachyon_WIN32.exe
```

### 3. 运行

```bash
# 中文界面
python orbital_viewer_zh.py

# English UI
python orbital_viewer.py
```

### 4. 打包 exe（可选）

```bash
pyinstaller orbital_viewer_zh.spec
```

## 命令行模式

```bash
# 批量处理文件夹，指定 HOMO+LUMO，等值面 0.05
python orbital_viewer.py folder/ --mo h,l --iso 0.05
```

## 项目结构

```
├── orbital_viewer.py       # English GUI
├── orbital_viewer_zh.py    # 中文界面
├── fchk_orbital.py         # 后端核心（生成 cube、VMD 控制、渲染）
├── fchk_orbital.ini        # 外部工具路径配置
├── orbital_viewer_zh.spec  # PyInstaller 打包配置
├── dist/
│   ├── OrbitalViewer_zh.exe  # 中文版预编译
│   └── OrbitalViewer_en.exe  # English 预编译
└── README.md
```

## 协议

学术用途。
