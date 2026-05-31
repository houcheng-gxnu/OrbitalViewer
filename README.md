# 🪐 OrbitalViewer

[![Bilibili](https://img.shields.io/badge/Bilibili-Tutorial-00A1D6?style=flat&logo=bilibili)](https://www.bilibili.com/video/BV1V5Gm6pEGr/)
[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat&logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Academic-blue?style=flat)](#license)

**一键串联 Multiwfn → VMD → Tachyon 工作流，从 fchk 到期刊精美轨道图，两分钟搞定。**

> 🏫 **广西师范大学 侯成课题组**  \> Guangxi Normal University, Hou Cheng Research Group

---

## ✨ 功能

- 🔬 **fchk → cube** — 调用 Multiwfn 自动生成 cube 文件，支持多轨道批量
- 🎥 **VMD 实时预览** — 多轨道同时显示，每轨道独立配色
- 🖼️ **Tachyon 光线追踪** — 输出高清 BMP/PNG，分辨率可达 3000+
- 🎚️ **等值面 & 透明度滑块** — 拖动滑块，VMD 中轨道面实时同步变化
- 🎨 **30+ 内置渲染风格** — 来自 vcube2.0、IboView、以及大量原创配色，下拉含色块预览
- 🏷️ **色块预览** — 样式下拉框直接显示正/负相等值面配色
- 🙈 **一键隐藏氢原子** — 突出重原子骨架，支持保留指定 H
- ✏️ **虚线绘制工具** — 标注氢键和分子间相互作用
- 📦 **批量处理** — 拖入文件夹，自动批处理出图
- 🌐 **双语界面** — 中文 / English 双版本

---

## 📥 下载

预编译 exe（无需安装 Python）：

| 版本 | 文件 |
|------|------|
| 中文版 | `dist/OrbitalViewer_zh.exe` |
| 英文版 | `dist/OrbitalViewer_en.exe` |

📁 **[浏览全部下载 →](https://cnb.cool/chem311/OrbitalViewer/-/tree/main/dist)**

---

## 🎬 视频教程

> [OrbitalViewer: From fchk to Publication-Ready Image in 2 Minutes](https://www.bilibili.com/video/BV1V5Gm6pEGr/)

---

## 🚀 快速开始

### 1. 依赖

| 组件 | 用途 | 安装 |
|------|------|------|
| Python 3.8+ | 运行环境 | — |
| PyQt5 | GUI 界面 | `pip install PyQt5` |
| [Multiwfn](http://sobereva.com/multiwfn/) | fchk → cube | 下载后配置路径 |
| [VMD](https://www.ks.uiuc.edu/Research/vmd/) | 3D 预览 + 渲染 | 安装后配置路径 |
| Tachyon | 光线追踪 | 随 VMD 附带 |

### 2. 配置工具路径

在 GUI 中直接浏览选择，或手动编辑 `fchk_orbital.ini`：

```ini
[paths]
multiwfn = E:\Multiwfn_2026.4.10_bin_Win64\Multiwfn.exe
vmd = C:\Program Files (x86)\University of Illinois\VMD\vmd.exe
tachyon = C:\Program Files (x86)\University of Illinois\VMD\tachyon_WIN32.exe
```

### 3. 启动

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

---

## 💻 命令行模式

```bash
# 批处理文件夹，HOMO + LUMO，等值面 0.05
python orbital_viewer.py folder/ --mo h,l --iso 0.05

# 指定轨道、样式、分辨率
python orbital_viewer.py input.fchk --mo h-1,h,l,l+1 --iso 0.04 --style lakers --res 3000,2250
```

---

## 🎨 内置样式一览

### vcube2.0（钟成）

| 样式 | 正相 | 负相 | 风格 |
|------|:----:|:----:|------|
| `sob_Gold` | 🟢 | 🔵 | 绿蓝高光，棕褐C |
| `Sob_Silver` | 🔵 | 🟡 | 灰蓝黄，光洁金属 |
| `sob_Special` | 🟣 | 🟡 | 紫金，珠宝概念 |
| `ao-shiny` | 🟠 | 🔵 | 橙青，珠宝AO |
| `ao-chalky` | 🟢 | 🔵 | 蓝绿，粉笔感AO |
| `white-green` | ⬜ | 🟢 | 白绿，塑料半透 |
| `white-red` | ⬜ | 🔴 | 白红，柔和粉笔 |
| `morandi-blue` | 🔵 | ⚫ | 莫兰迪蓝白，磨砂 |
| `morandi-green` | 🟢 | ⬜ | 莫兰迪绿白，不透明 |
| `morandi-orange` | 🟠 | 🔵 | 莫兰迪橙蓝 |
| `morandi-red` | 🔴 | ⬜ | 莫兰迪红白 |
| `vmwfn0` | 🔵 | ⬜ | 白冰蓝，光滑半透 |
| `vmwfn1` | ⬜ | 🔴 | 红白，光滑漆面 |

### IboView 风格

| 样式 | 正相 | 负相 | 风格 |
|------|:----:|:----:|------|
| `iboview-shiny` | 🔵 | 🔴 | 高光蓝红 |
| `iboview-gold` | 🟢 | 🔵 | 金色绿蓝 |
| `iboview-crystal` | 🔵 | 💗 | 水晶青粉 |
| `iboview-dark` | 🟣 | 🟠 | 暗黑紫橙 |
| `iboview-green-pink` | 🟢 | 💗 | 绿粉双色 |
| `iboview-purple-blue` | 🟣 | 🔵 | 紫蓝神秘 |
| `iboview-cyan-yellow` | 🔵 | 🟡 | 青黄明亮 |
| `iboview-orange-teal` | 🟠 | 🔵 | 橙青温暖 |
| `iboview-red-green` | 🔴 | 🟢 | 红绿互补 |
| `iboview-rainbow` | 💗 | 🔵 | 彩虹多彩 |

### 原创精选配色

| 样式 | 正相 | 负相 | 风格 |
|------|:----:|:----:|------|
| `aurora-teal` | 🔵 | 💗 | 极光青 / 珊瑚粉 |
| `midnight-gold` | 🔵 | 🟡 | 午夜靛蓝 / 琥珀金 |
| `lavender-mint` | 🟣 | 🟢 | 薰衣草紫 / 薄荷绿 |
| `sunset-fire` | 🟠 | 🔵 | 日落暖橙 / 深蓝紫 |
| `ocean-depth` | 🔵 | 🟢 | 深海蓝 / 海泡绿 |
| `rose-quartz` | 💗 | 🔵 | 玫瑰粉 / 灰蓝 |
| `forest-emerald` | 🟢 | 🟤 | 翡翠绿 / 铜棕 |
| `neon-cyber` | 🟣 | 🔵 | 电光紫 / 霓虹青 |
| `cherry-blossom` | 💗 | 🔵 | 樱花粉 / 淡天蓝 |
| `graphite-ink` | ⚫ | 🔴 | 石墨黑 / 朱砂红 |
| `lakers` | 🟣 | 🟡 | 湖人紫 / 冠军金 |

---

## 📁 项目结构

```
├── orbital_viewer.py          # 英文 GUI
├── orbital_viewer_zh.py       # 中文 GUI
├── fchk_orbital.py            # 后端引擎（cube生成、VMD控制、渲染）
├── fchk_orbitalibo.py         # IGMH 等值面可视化
├── fchk_orbitalibo2.py        # IGMH 增强版（IboView 风格）
├── log_render.py / log_render_qt.py  # 日志渲染工具
├── fchk_orbital.ini           # 外部工具路径配置
├── orbital_viewer_zh.spec     # PyInstaller 打包配置
├── tutorial_script.md         # 视频教程脚本
├── dist/                      # 预编译 exe
└── README.md
```

---

## 📚 致谢

### Multiwfn

本软件的核心计算引擎来自 **卢天老师** 开发的 [**Multiwfn**](http://sobereva.com/multiwfn/) 多功能波函数分析程序，特此致以最诚挚的感谢！

> Tian Lu, Feiwu Chen, *Multiwfn: A Multifunctional Wavefunction Analyzer*, J. Comput. Chem., **2012**, 33, 580–592. [DOI: 10.1002/jcc.22885](https://doi.org/10.1002/jcc.22885)

> Tian Lu, *A Comprehensive Electron Wavefunction Analysis Toolbox for Chemists, Multiwfn*, J. Chem. Phys., **2024**, 161, 082503. [DOI: 10.1063/5.0216272](https://doi.org/10.1063/5.0216272) *(JCP Editors' Choice 2024)*

Multiwfn 目前已被超过 **4 万篇论文** 引用，用户遍布全球 **90 余国**。

### vcube2.0

渲染样式系统源自 [**vcube2.0**](https://github.com/zhongcheng-1998/vcube2.0)（钟成），提供了 11 套精美的 VMD 轨道渲染配置。

### VMD

> Humphrey, W., Dalke, A. and Schulten, K., *VMD: Visual Molecular Dynamics*, J. Molec. Graphics, **1996**, 14, 33–38.

### Tachyon

> Stone, J. E., *An Efficient Library for Parallel Ray Tracing and Animation*, M.Sc. Thesis, University of Missouri-Rolla, **1998**.

---

## 📄 License

学术用途。如需引用本软件，请同时引用上述 Multiwfn 文献。

---

*OrbitalViewer — make your orbitals look as good as your science.*
