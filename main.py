#!/usr/bin/env python3
"""
轨道等值面可视化工具 v5.3 — 入口模块
用法:
    python main.py                        # 启动 GUI
    python main.py input.fchk --mo h     # 命令行批处理模式
"""

import os
import sys
import glob

# 确保当前目录在 sys.path 中，以便能找到本地模块和 backend
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main_window import OrbitalVisApp


def main():
    if len(sys.argv) > 1:
        import argparse
        import fchk_orbital as backend

        p = argparse.ArgumentParser(
            description="Multiwfn + VMD/Tachyon Orbital Isosurface Visualization v5.3")
        p.add_argument("input", help="fchk file or folder")
        p.add_argument("--mo", default="h", help="Orbital (h/l/h-1/number)")
        p.add_argument("--iso", type=float, default=0.05, help="Isosurface threshold")
        p.add_argument("--grid", default="2", help="Grid quality (1/2/3)")
        p.add_argument("--style", default="sob-art",
                       choices=list(backend.STYLES.keys()), help="Render style")
        p.add_argument("--res", default="2000,1500", help="Resolution width,height")
        p.add_argument("--no-render", action="store_true", help="Generate cube only")
        p.add_argument("--out", default=None)
        a = p.parse_args()

        files = (sorted(glob.glob(os.path.join(a.input, "*.fchk")))
                 if os.path.isdir(a.input) else [a.input])
        out = a.out or (os.path.dirname(a.input)
                        if os.path.isfile(a.input) else a.input)
        os.makedirs(out, exist_ok=True)

        w, h = [int(x) for x in a.res.split(",")]

        for i, f in enumerate(files):
            print(f"[{i+1}/{len(files)}] {os.path.basename(f)}")
            cube = backend.gen_cube(f, orbital=a.mo, grid_quality=int(a.grid),
                                    work_dir=out)
            if cube:
                print(f"  cube: {os.path.basename(cube)}")
                if not a.no_render:
                    png = backend.render_cube_auto(
                        cube, isovalue=a.iso, style_name=a.style,
                        resolution=(w, h))
                    if png:
                        print(f"  png:  {os.path.basename(png)}")
            else:
                print(f"  Failed")
    else:
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtGui import QColor, QPalette

        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        # Uniform tooltip background
        tip_pal = app.palette()
        tip_pal.setColor(QPalette.ToolTipBase, QColor("#FFFFFF"))
        tip_pal.setColor(QPalette.ToolTipText, QColor("#2C3E50"))
        app.setPalette(tip_pal)
        window = OrbitalVisApp()
        window.show()
        sys.exit(app.exec_())


if __name__ == "__main__":
    main()
