# OrbitalViewer

分子轨道等值面可视化工具 v5.1 — Multiwfn + VMD + Tachyon 一体化 GUI。

Molecular orbital isosurface visualization tool — streamlined GUI for Multiwfn, VMD, and Tachyon.

## 视频教程

[![轨道等值面可视化工具大升级！](https://img.shields.io/badge/Bilibili-视频教程-00A1D6?style=flat&logo=bilibili)](https://www.bilibili.com/video/BV1spGC68Eej/)

> 🎬 [轨道等值面可视化工具大升级！PyQt5 重写，颜值与体验双双起飞](https://www.bilibili.com/video/BV1spGC68Eej/)

## 功能

- **fchk 文件 → 轨道 cube 文件**（调用 Multiwfn）
- **VMD 实时预览** 轨道等值面（支持多轨道同时预览）
- **Tachyon 光线追踪渲染** 导出高质量 BMP/PNG 图片
- **多轨道选择**：HOMO / LUMO / 自定义索引 / 范围选择（如 `h-1,h,l,l+1`）
- **可调节参数**：等值面值 (isovalue)、格点质量、渲染样式
- **多种内置渲染样式**：sob_Gold、CPK、Licorice 等
- **中英双语界面**（`orbital_viewer_zh.py` 中文版 / `orbital_viewer.py` English）

## 依赖

| 依赖 | 用途 | 说明 |
|------|------|------|
| Python 3.8+ | 运行环境 | — |
| PyQt5 | GUI 框架 | `pip install PyQt5` |
| [Multiwfn](http://sobereva.com/multiwfn/) | fchk → cube 转换 | 需下载并配置路径 |
| [VMD](https://www.ks.uiuc.edu/Research/vmd/) | 3D 预览 + Tachyon 渲染 | 需安装并配置路径 |
| Tachyon | 光线追踪渲染 | 随 VMD 一同安装 |

## 快速开始

### 1. 安装 Python 依赖

```bash
pip install PyQt5
```

### 2. 配置外部工具路径

编辑 `fchk_orbital.ini`，设置 Multiwfn、VMD、Tachyon 的路径：

```ini
[paths]
multiwfn = E:\Multiwfn_2026.4.10_bin_Win64\Multiwfn.exe
vmd = C:\Program Files (x86)\University of Illinois\VMD\vmd.exe
tachyon = C:\Program Files (x86)\University of Illinois\VMD\tachyon_WIN32.exe
```

### 3. 运行

```bash
# 中文版
python orbital_viewer_zh.py

# English version
python orbital_viewer.py
```

### 4. 打包为 exe（可选）

```bash
pyinstaller orbital_viewer_zh.spec
```

## 使用流程

1. **选择 fchk 文件** — 从 Gaussian 计算输出的 `.fchk` 文件
2. **选择轨道** — 点击「选择轨道」，勾选需要的轨道（HOMO、LUMO 等）
3. **生成 Cube** — 调用 Multiwfn 将轨道转换为 cube 格点文件
4. **预览** — 在 VMD 中查看 3D 等值面
5. **渲染** — 用 Tachyon 光线追踪出图

## 项目结构

```
├── orbital_viewer.py       # 英文版 GUI
├── orbital_viewer_zh.py    # 中文版 GUI
├── fchk_orbital.py         # 后端逻辑（cube生成、VMD控制、渲染）
├── fchk_orbital.ini        # 外部工具路径配置
├── orbital_viewer_zh.spec  # PyInstaller 打包配置
└── README.md
```

## License

This project is for academic use.
