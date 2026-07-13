# OrbitalViewer 5.3

基于 Multiwfn + VMD + Tachyon 的分子轨道等值面可视化工具。

## 功能特性

**拖放加载** — 支持 `.fchk`、`.log`、`.out`、`.cub`、`.cube`、`.xyz`，拖入即识别，原子与化学键自动渲染。

**轨道浏览器** — 表格展示所有轨道（编号、能量、eV、占据数），开壳层 α/β 自动分两标签紧邻排列。箭头 emoji 表示占据态（⬆️⬇️ 双占据 / ⬆️ α 单电子 / ⬇️ β 单电子 / ⬜ 空）。双击任意行自动生成 cube 并发送至 VMD。

**四线渲染** — 支持 Solid、CPK、Sob-Multi、Sob-Art 四种风格，可选透明背景、有/无阴影、Tachyon 路径自定义。

**虚线模式** — 一键锁定选中原子对，画布与 VMD 同步绘制虚线键。颜色 8 种、线型 5 种（圆点/虚线/圆柱/锥形/线段），下拉即时生效。

**高级叠加** — 选中两条轨道同步生成 cube 与渲染，叠加对比。

**中英双语** — UI 即时切换，无需重启。

**命令行批处理** — 支持文件夹批量生成 cube 与渲染。

**运行日志** — QTextCursor 原生实现，16px 等宽字体，彩色标签（VMD / OK / ERR / GEN），带时间戳。

## 快速开始

```bash
# 安装依赖
pip install PyQt5 numpy

# 下载 Multiwfn 和 VMD，确保可执行文件在 PATH 中

# 启动 GUI
python main.py

# 命令行批处理
python main.py input.fchk --mo h --iso 0.05 --style sob-art
python main.py ./fchk_folder/ --mo h --iso 0.04 --grid 3 --no-render
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `input` | fchk 文件或文件夹路径 | — |
| `--mo` | 轨道选择 (h / l / h-1 / 数字) | h |
| `--iso` | 等值面阈值 | 0.05 |
| `--grid` | 网格质量 (1/2/3) | 2 |
| `--style` | 渲染风格 | sob-art |
| `--res` | 分辨率 (宽,高) | 2000,1500 |
| `--no-render` | 仅生成 cube | — |
| `--out` | 输出目录 | 输入文件所在目录 |

## 项目结构

```
OrbitalViewer 5.3/
├── main.py              # 入口（GUI + 命令行）
├── main_window.py       # 主窗口（UI 布局、交互逻辑）
├── molcanvas.py         # 分子结构画布（Qt 自定义绘制）
├── fchk_orbital.py      # 后端核心（cube 生成、渲染管道）
├── fchk_parser.py       # fchk 轨道信息解析
├── orbital_viewer_lib.py # 共享工具库
├── workers.py           # QThread 后台工作线程
├── widgets.py           # 自定义 QSS 控件
├── dialogs.py           # 对话框
├── i18n.py              # 中英文翻译
├── theme.py             # QSS 主题样式
├── orbital_viewer_v53.py # 旧版兼容层
└── OrbitalViewer.spec   # PyInstaller 打包配置
```

## 外部依赖

- [Multiwfn](http://sobereva.com/multiwfn/) — 从 fchk 生成 cube 文件
- [VMD](https://www.ks.uiuc.edu/Research/vmd/) — 分子可视化与渲染
- [Tachyon](http://jedi.ks.uiuc.edu/~johns/raytracer/) — 光线追踪渲染（随 VMD 分发）

## 编译

```bash
pip install pyinstaller
pyinstaller OrbitalViewer.spec --clean
```

输出在 `dist/OrbitalViewer.exe`，单文件、无控制台。

## 许可证

MIT License
