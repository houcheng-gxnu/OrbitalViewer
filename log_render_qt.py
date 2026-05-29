#!/usr/bin/env python3
"""
log 分子结构渲染工具 v1.2 (PyQt 中文版)
Multiwfn (log → xyz) + VMD (预览 + Tachyon 渲染) + Tachyon (scene → BMP/PNG)

PyQt5 重写，清爽浅色科技风界面，微软雅黑字体。
后端逻辑全部引入自 log_render.py。
"""

import os
import sys
import glob
import subprocess
import threading
import socket
import time
import shutil
import tempfile

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QRadioButton, QCheckBox,
    QComboBox, QTextEdit, QFileDialog, QMessageBox, QButtonGroup,
    QFrame, QGridLayout, QSizePolicy, QTabWidget,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette, QTextCursor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import log_render as backend


LIGHT_QSS = """
QWidget {
    font-family: "Microsoft YaHei", "Segoe UI", "Consolas", sans-serif;
    font-size: 9.5pt;
    color: #2C3E50;
}

QMainWindow {
    background-color: #E4EAF2;
}

QGroupBox {
    border: 1px solid #C8D6E5;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 8px;
    font-weight: bold;
    font-size: 9.5pt;
    color: #2C3E50;
    background-color: #FFFFFF;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}

QTabWidget::pane {
    border: 1px solid #C8D6E5;
    border-radius: 4px;
    background-color: #FFFFFF;
    padding: 4px;
}

QTabBar::tab {
    background-color: #E8ECF4;
    border: 1px solid #C8D6E5;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 28px;
    margin-right: 3px;
    font-weight: bold;
    font-size: 9.5pt;
    color: #576574;
    min-width: 80px;
}

QTabBar::tab:selected {
    background-color: #FFFFFF;
    color: #1565C0;
    border-bottom: 2px solid #1565C0;
}

QTabBar::tab:hover:!selected {
    background-color: #F0F3F8;
    color: #1E88E5;
}

QPushButton {
    background-color: #E8ECF4;
    border: 1px solid #C8D6E5;
    border-radius: 4px;
    padding: 5px 14px;
    font-weight: bold;
    font-size: 9pt;
    color: #2C3E50;
}

QPushButton:hover {
    background-color: #D6DEEA;
    border-color: #1565C0;
}

QPushButton:pressed {
    background-color: #C8D6E5;
}

QPushButton#PrimaryBtn {
    background-color: #1565C0;
    color: #FFFFFF;
    border: 1px solid #0D47A1;
    font-size: 9.5pt;
    padding: 6px 18px;
}

QPushButton#PrimaryBtn:hover {
    background-color: #1E88E5;
}

QPushButton#RenderBtn {
    background-color: #2E7D32;
    color: #FFFFFF;
    border: 1px solid #1B5E20;
    font-size: 9.5pt;
    padding: 6px 18px;
}

QPushButton#RenderBtn:hover {
    background-color: #388E3C;
}

QPushButton#StopBtn {
    background-color: #C62828;
    color: #FFFFFF;
    border: 1px solid #B71C1C;
    font-size: 9.5pt;
    padding: 6px 18px;
}

QPushButton#StopBtn:hover {
    background-color: #E53935;
}

QPushButton#SmallBtn {
    padding: 3px 8px;
    font-size: 8.5pt;
    min-width: 35px;
}

QPushButton:disabled {
    background-color: #ECF0F5;
    color: #AAB5C0;
    border-color: #D5DDE5;
}

QLineEdit, QComboBox {
    border: 1px solid #C8D6E5;
    border-radius: 3px;
    padding: 3px 6px;
    background-color: #F8FAFC;
    font-size: 9pt;
}

QLineEdit:focus, QComboBox:focus {
    border-color: #1565C0;
    background-color: #FFFFFF;
}

QComboBox::drop-down {
    border: none;
    padding-right: 6px;
}

QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    border: 1px solid #C8D6E5;
    selection-background-color: #E3F2FD;
    selection-color: #1565C0;
}

QSlider::groove:horizontal {
    border: 1px solid #C8D6E5;
    height: 6px;
    background: #E8ECF4;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #1565C0;
    border: 1px solid #0D47A1;
    width: 16px;
    margin: -5px 0;
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background: #1E88E5;
}

QCheckBox {
    spacing: 6px;
}

QCheckBox::indicator {
    width: 15px;
    height: 15px;
}

QRadioButton {
    spacing: 6px;
}

QRadioButton::indicator {
    width: 15px;
    height: 15px;
}

QTextEdit {
    border: 1px solid #C8D6E5;
    border-radius: 3px;
    background-color: #F8FAFC;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 9pt;
    padding: 4px;
}

QLabel#TitleLabel {
    font-size: 13pt;
    font-weight: bold;
    color: #1565C0;
    letter-spacing: 2px;
}

QLabel#SubTitleLabel {
    font-size: 9pt;
    color: #78909C;
}

QLabel#ProgressLabel {
    font-size: 9pt;
    font-weight: bold;
    color: #1565C0;
    padding: 2px 6px;
    background-color: #E3F2FD;
    border-radius: 3px;
}

QLabel#HintLabel {
    font-size: 8.5pt;
    color: #90A4AE;
}
"""


class SciFiGroupBox(QGroupBox):
    def __init__(self, title, parent=None):
        super().__init__(title, parent)


class LogWorker(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, int, int, list)

    def __init__(self, files, out_dir, style_name, representation,
                 cpk_scale, resolution, shade_mode, keep_h_indices,
                 auto_render, exe_paths, do_open):
        super().__init__()
        self.files = files
        self.out_dir = out_dir
        self.style_name = style_name
        self.representation = representation
        self.cpk_scale = cpk_scale
        self.resolution = resolution
        self.shade_mode = shade_mode
        self.keep_h_indices = keep_h_indices
        self.auto_render = auto_render
        self.exe_paths = exe_paths
        self.do_open = do_open
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        total = len(self.files)
        self.log_signal.emit(f"{total} 个文件 -> {self.out_dir}")
        self.log_signal.emit(
            f"样式={self.style_name}  表示={self.representation}  "
            f"缩放={self.cpk_scale}  分辨率={self.resolution[0]}x{self.resolution[1]}")
        self.log_signal.emit("流程: log -> Multiwfn(xyz) -> VMD/Tachyon(PNG)")
        if self.auto_render:
            self.log_signal.emit("模式: 自动渲染 (无预览)")
        else:
            self.log_signal.emit("模式: 预览 -> 手动调整 -> 渲染")
        self.log_signal.emit("=" * 50)

        ok = 0
        xyz_files = []
        t_total = time.time()

        self.log_signal.emit("\n[步骤1] Multiwfn: log -> xyz")
        for i, log_file in enumerate(self.files):
            if not self._running:
                self.log_signal.emit("已停止")
                break
            name = os.path.basename(log_file)
            self.progress_signal.emit(f"[转换 {i+1}/{total}] {name}")
            self.log_signal.emit(f"\n[转换 {i+1}/{total}] {name}")

            t0 = time.time()
            xyz = backend.log_to_xyz(
                log_file, multiwfn_exe=self.exe_paths["multiwfn"],
                work_dir=self.out_dir)
            dt = time.time() - t0
            if not xyz:
                self.log_signal.emit(f"  xyz 转换失败 ({dt:.1f}s)")
                continue
            self.log_signal.emit(f"  xyz 完成 ({dt:.1f}s) -> {os.path.basename(xyz)}")
            xyz_files.append(xyz)

        if not self._running:
            pass
        elif not self.auto_render and xyz_files:
            xyz_file = xyz_files[0]
            name = os.path.basename(xyz_file)
            self.progress_signal.emit(f"[预览] {name}")
            self.log_signal.emit(f"\n[步骤2] VMD 预览: {name}")
            try:
                port, render_dir = backend.preview_mol(
                    xyz_file, style_name=self.style_name,
                    representation=self.representation,
                    cpk_scale=str(self.cpk_scale),
                    vmd_exe=self.exe_paths["vmd"],
                    shade_mode=self.shade_mode,
                    keep_h_indices=self.keep_h_indices)
                if port:
                    self.log_signal.emit(f"VMD 已启动 (端口 {port})")
                    self.finished_signal.emit(
                        False, len(xyz_files), total, [(xyz_file, port, render_dir)])
                else:
                    self.log_signal.emit("VMD 启动失败")
                    self.finished_signal.emit(False, 0, total, [])
            except Exception as e:
                self.log_signal.emit(f"VMD 启动错误: {e}")
                self.finished_signal.emit(False, 0, total, [])
        elif self.auto_render:
            self.log_signal.emit(f"\n[步骤2] 自动渲染 {len(xyz_files)} 个文件")
            for i, xyz_file in enumerate(xyz_files):
                if not self._running:
                    self.log_signal.emit("已停止")
                    break
                name = os.path.basename(xyz_file)
                stem = os.path.splitext(name)[0]
                self.progress_signal.emit(f"[渲染 {i+1}/{len(xyz_files)}] {name}")
                self.log_signal.emit(f"\n[渲染 {i+1}/{len(xyz_files)}] {name}")

                t0 = time.time()
                png = os.path.join(self.out_dir, f"{stem}.png")
                try:
                    result = backend.render_mol_auto(
                        xyz_file, output_png=png,
                        style_name=self.style_name,
                        representation=self.representation,
                        cpk_scale=str(self.cpk_scale),
                        resolution=self.resolution,
                        vmd_exe=self.exe_paths["vmd"],
                        tachyon_exe=self.exe_paths["tachyon"],
                        shade_mode=self.shade_mode,
                        keep_h_indices=self.keep_h_indices)
                    dt = time.time() - t0
                    if result:
                        self.log_signal.emit(f"  PNG: {os.path.basename(result)} ({dt:.1f}s)")
                        ok += 1
                    else:
                        self.log_signal.emit(f"  渲染失败 ({dt:.1f}s)")
                except Exception as e:
                    self.log_signal.emit(f"  错误: {e}")

            elapsed = time.time() - t_total
            self.log_signal.emit(f"\n全部完成: {ok}/{len(xyz_files)}, 用时 {elapsed:.1f}s")
            self.finished_signal.emit(True, ok, len(xyz_files), [])

    def _log_fchk_to_png_name(self, log_path, orbital):
        stem = os.path.splitext(os.path.basename(log_path))[0]
        return os.path.join(self.out_dir, f"{stem}_{orbital}.png")


class RenderWorker(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str)

    def __init__(self, port, render_dir, output_png, tachyon_exe,
                 resolution, style_name, shade_mode):
        super().__init__()
        self.port = port
        self.render_dir = render_dir
        self.output_png = output_png
        self.tachyon_exe = tachyon_exe
        self.resolution = resolution
        self.style_name = style_name
        self.shade_mode = shade_mode

    def run(self):
        self.log_signal.emit(f"\n正在渲染当前视角 (风格: {self.style_name})...")
        t0 = time.time()
        try:
            png = backend.render_current_view(
                self.port, self.render_dir,
                output_png=self.output_png,
                tachyon_exe=self.tachyon_exe,
                resolution=self.resolution,
                style_name=self.style_name,
                shade_mode=self.shade_mode,
            )
            dt = time.time() - t0
            if png:
                self.log_signal.emit(f"渲染完成 ({dt:.1f}s) -> {os.path.basename(png)}")
                self.finished_signal.emit(png)
            else:
                self.log_signal.emit(f"渲染失败 ({dt:.1f}s)")
                self.finished_signal.emit("")
        except Exception as e:
            self.log_signal.emit(f"渲染错误: {e}")
            self.finished_signal.emit("")


class LogRenderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("分子结构渲染 v1.2 — Multiwfn + VMD/Tachyon [PyQt 中文版]")
        self.resize(920, 780)
        self.setMinimumSize(840, 680)

        self.paths = backend.load_config()
        self.running = False
        self.vmd_port = None
        self.vmd_render_dir = None
        self.vmd_xyz_path = None
        self._vmd_persist_sock = None
        self.vmd_style_name = "sob_Gold"
        self.vmd_representation = "CPK"
        self.vmd_cpk_scale = "1.0"
        self.vmd_shade_mode = "full"
        self._current_rep_style = "CPK 0.600000 0.400000 30.000000 30.000000"
        self._current_rep_material = "_stl_atom"

        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(12, 8, 12, 10)
        main_layout.setSpacing(6)

        title_label = QLabel("◆  分子结构渲染  ◆")
        title_label.setObjectName("TitleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        sub_label = QLabel("Multiwfn + VMD + Tachyon  |  v1.2 PyQt 中文版")
        sub_label.setObjectName("SubTitleLabel")
        sub_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(sub_label)

        self.tabs = QTabWidget()

        tab_setup = QWidget()
        tab_setup_layout = QVBoxLayout(tab_setup)
        tab_setup_layout.setContentsMargins(4, 4, 4, 4)
        tab_setup_layout.setSpacing(6)
        tab_setup_layout.addWidget(self._build_paths_panel())
        tab_setup_layout.addWidget(self._build_input_panel())
        tab_setup_layout.addWidget(self._build_output_panel())
        tab_setup_layout.addStretch()
        self.tabs.addTab(tab_setup, "📁  路径设置")

        tab_params = QWidget()
        tab_params_layout = QVBoxLayout(tab_params)
        tab_params_layout.setContentsMargins(4, 4, 4, 4)
        tab_params_layout.setSpacing(6)
        tab_params_layout.addWidget(self._build_render_params_panel())
        tab_params_layout.addStretch()
        self.tabs.addTab(tab_params, "🎨  渲染参数")

        tab_preview = QWidget()
        tab_preview_layout = QVBoxLayout(tab_preview)
        tab_preview_layout.setContentsMargins(4, 4, 4, 4)
        tab_preview_layout.setSpacing(6)
        tab_preview_layout.addWidget(self._build_buttons_panel())
        tab_preview_layout.addStretch()
        self.tabs.addTab(tab_preview, "▶️  预览运行")

        tab_tools = QWidget()
        tab_tools_layout = QVBoxLayout(tab_tools)
        tab_tools_layout.setContentsMargins(4, 4, 4, 4)
        tab_tools_layout.setSpacing(6)
        tab_tools_layout.addWidget(self._build_hydrogen_panel())
        tab_tools_layout.addWidget(self._build_draw_bond_panel())
        tab_tools_layout.addStretch()
        self.tabs.addTab(tab_tools, "🛠️  工具")

        main_layout.addWidget(self.tabs, stretch=3)

        self.progress_label = QLabel("◆  就绪")
        self.progress_label.setObjectName("ProgressLabel")
        main_layout.addWidget(self.progress_label)

        log_frame = QFrame()
        log_layout = QVBoxLayout(log_frame)
        log_layout.setContentsMargins(0, 0, 0, 0)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(120)
        self.log_text.setMaximumHeight(200)
        log_layout.addWidget(self.log_text)

        main_layout.addWidget(log_frame)

    def _build_paths_panel(self):
        grp = SciFiGroupBox("软件路径")
        layout = QGridLayout(grp)
        layout.setVerticalSpacing(4)
        layout.setHorizontalSpacing(6)

        layout.addWidget(QLabel("Multiwfn:"), 0, 0)
        self.var_mw = QLineEdit(self.paths["multiwfn"])
        self.var_mw.setPlaceholderText("Multiwfn.exe 路径")
        layout.addWidget(self.var_mw, 0, 1)
        btn = QPushButton("浏览")
        btn.setObjectName("SmallBtn")
        btn.clicked.connect(lambda: self._browse_exe("multiwfn"))
        layout.addWidget(btn, 0, 2)

        layout.addWidget(QLabel("VMD:"), 1, 0)
        self.var_vmd = QLineEdit(self.paths["vmd"])
        self.var_vmd.setPlaceholderText("vmd.exe 路径")
        layout.addWidget(self.var_vmd, 1, 1)
        btn = QPushButton("浏览")
        btn.setObjectName("SmallBtn")
        btn.clicked.connect(lambda: self._browse_exe("vmd"))
        layout.addWidget(btn, 1, 2)

        layout.setColumnStretch(1, 1)
        return grp

    def _build_input_panel(self):
        grp = SciFiGroupBox("输入文件")
        layout = QHBoxLayout(grp)
        layout.setSpacing(6)

        self.mode_group = QButtonGroup(self)
        rb_folder = QRadioButton("文件夹")
        rb_file = QRadioButton("单个文件")
        self.mode_group.addButton(rb_folder, 0)
        self.mode_group.addButton(rb_file, 1)
        rb_file.setChecked(True)
        layout.addWidget(rb_folder)
        layout.addWidget(rb_file)

        self.var_path = QLineEdit()
        self.var_path.setPlaceholderText("选择 .log 文件或文件夹...")
        layout.addWidget(self.var_path, stretch=1)
        btn = QPushButton("浏览")
        btn.clicked.connect(self._browse_input)
        layout.addWidget(btn)

        return grp

    def _build_output_panel(self):
        grp = SciFiGroupBox("输出目录")
        layout = QHBoxLayout(grp)
        layout.setSpacing(6)

        hint = QLabel("(默认: 与输入相同)")
        hint.setObjectName("HintLabel")
        layout.addWidget(hint)

        self.var_out = QLineEdit()
        self.var_out.setPlaceholderText("输出目录...")
        layout.addWidget(self.var_out, stretch=1)
        btn = QPushButton("浏览")
        btn.clicked.connect(self._browse_out)
        layout.addWidget(btn)

        return grp

    def _build_render_params_panel(self):
        grp = SciFiGroupBox("渲染参数")
        rlayout = QGridLayout(grp)
        rlayout.setVerticalSpacing(4)
        rlayout.setHorizontalSpacing(6)

        rlayout.addWidget(QLabel("风格:"), 0, 0)
        style_names = list(backend.STYLES.keys())
        self.var_style = QComboBox()
        self.var_style.addItems(style_names)
        self.var_style.setCurrentIndex(0)
        self.var_style.currentIndexChanged.connect(self._on_style_change)
        rlayout.addWidget(self.var_style, 0, 1, 1, 2)

        rlayout.addWidget(QLabel("表示:"), 1, 0)
        self.var_rep = QComboBox()
        self.var_rep.addItems(list(backend.REPRESENTATIONS.keys()))
        self.var_rep.setCurrentIndex(0)
        rlayout.addWidget(self.var_rep, 1, 1)

        rlayout.addWidget(QLabel("缩放:"), 1, 2)
        self.var_scale = QLineEdit("1.0")
        self.var_scale.setMaximumWidth(50)
        rlayout.addWidget(self.var_scale, 1, 3)
        hint = QLabel("(CPK/VDW 半径比)")
        hint.setObjectName("HintLabel")
        rlayout.addWidget(hint, 1, 4)

        rlayout.addWidget(QLabel("分辨率:"), 2, 0)
        self.var_res = QComboBox()
        self.var_res.addItems(["2000x1500", "1200x900", "3000x2250"])
        self.var_res.setCurrentIndex(0)
        self.var_res.setMaximumWidth(120)
        rlayout.addWidget(self.var_res, 2, 1)

        rlayout.addWidget(QLabel("光影:"), 2, 2)
        shade_frame = QHBoxLayout()
        shade_frame.setSpacing(4)
        self.shade_group = QButtonGroup(self)
        rb_full = QRadioButton("完整")
        rb_medium = QRadioButton("中等")
        self.shade_group.addButton(rb_full, 0)
        self.shade_group.addButton(rb_medium, 1)
        rb_full.setChecked(True)
        shade_frame.addWidget(rb_full)
        shade_frame.addWidget(rb_medium)
        rlayout.addLayout(shade_frame, 2, 3, 1, 2)

        mode_frame = QHBoxLayout()
        mode_frame.setSpacing(8)
        self.var_auto = QCheckBox("自动渲染 (无预览, 批处理模式)")
        self.var_open = QCheckBox("完成后打开文件夹")
        mode_frame.addWidget(self.var_auto)
        mode_frame.addWidget(self.var_open)
        mode_frame.addStretch()
        rlayout.addLayout(mode_frame, 3, 0, 1, 5)

        for c in range(5):
            rlayout.setColumnStretch(c, 0)
        rlayout.setColumnStretch(1, 1)
        return grp

    def _build_buttons_panel(self):
        grp = SciFiGroupBox("操作")
        layout = QHBoxLayout(grp)
        layout.setSpacing(8)

        self.btn_run = QPushButton("◆  生成 XYZ & 预览")
        self.btn_run.setObjectName("PrimaryBtn")
        self.btn_run.clicked.connect(self._run)
        layout.addWidget(self.btn_run)

        self.btn_preview = QPushButton("◇  预览 (已选文件)")
        self.btn_preview.clicked.connect(self._preview)
        layout.addWidget(self.btn_preview)

        self.btn_render = QPushButton("◆  渲染当前视角")
        self.btn_render.setObjectName("RenderBtn")
        self.btn_render.setEnabled(False)
        self.btn_render.clicked.connect(self._render_view)
        layout.addWidget(self.btn_render)

        self.btn_stop = QPushButton("■  停止")
        self.btn_stop.setObjectName("StopBtn")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop)
        layout.addWidget(self.btn_stop)

        layout.addStretch()
        return grp

    def _build_hydrogen_panel(self):
        grp = SciFiGroupBox("隐藏氢原子")
        layout = QHBoxLayout(grp)
        layout.setSpacing(8)

        self.btn_h_filter = QPushButton("隐藏所有氢原子")
        self.btn_h_filter.setEnabled(False)
        self.btn_h_filter.clicked.connect(self._toggle_h_filter)
        layout.addWidget(self.btn_h_filter)

        layout.addWidget(QLabel("保留编号 (逗号分隔):"))
        self.var_h_indices = QLineEdit()
        self.var_h_indices.setMaximumWidth(180)
        self.var_h_indices.setPlaceholderText("留空 = 全部隐藏")
        layout.addWidget(self.var_h_indices)

        layout.addStretch()
        return grp

    def _build_draw_bond_panel(self):
        grp = SciFiGroupBox("绘制虚线键")
        layout = QGridLayout(grp)
        layout.setVerticalSpacing(4)
        layout.setHorizontalSpacing(6)

        bond_colors_cn = ["黑色", "灰色", "青色", "黄色", "红色", "蓝色",
                          "绿色", "白色", "橙色", "紫色"]
        bond_types_cn = ["虚线(pymol)", "圆点(dots)", "实线圆柱", "球体", "圆锥", "线条"]
        bond_mats_cn = ["不透明", "50%透明", "透明"]

        row = 0
        layout.addWidget(QLabel("原子 1:"), row, 0)
        self.var_bond_atom1 = QLineEdit("0")
        self.var_bond_atom1.setMaximumWidth(50)
        layout.addWidget(self.var_bond_atom1, row, 1)

        layout.addWidget(QLabel("原子 2:"), row, 2)
        self.var_bond_atom2 = QLineEdit("1")
        self.var_bond_atom2.setMaximumWidth(50)
        layout.addWidget(self.var_bond_atom2, row, 3)

        layout.addWidget(QLabel("颜色:"), row, 4)
        self.var_bond_color = QComboBox()
        self.var_bond_color.addItems(bond_colors_cn)
        self.var_bond_color.setCurrentIndex(2)
        self.var_bond_color.setMaximumWidth(80)
        layout.addWidget(self.var_bond_color, row, 5)

        row += 1
        layout.addWidget(QLabel("类型:"), row, 0)
        self.var_bond_type = QComboBox()
        self.var_bond_type.addItems(bond_types_cn)
        self.var_bond_type.setCurrentIndex(1)
        self.var_bond_type.setMaximumWidth(110)
        layout.addWidget(self.var_bond_type, row, 1)

        layout.addWidget(QLabel("材质:"), row, 2)
        self.var_bond_mat = QComboBox()
        self.var_bond_mat.addItems(bond_mats_cn)
        self.var_bond_mat.setCurrentIndex(1)
        self.var_bond_mat.setMaximumWidth(130)
        layout.addWidget(self.var_bond_mat, row, 3)

        layout.addWidget(QLabel("段数:"), row, 4)
        self.var_bond_nbars = QLineEdit("10")
        self.var_bond_nbars.setMaximumWidth(40)
        layout.addWidget(self.var_bond_nbars, row, 5)

        row += 1
        layout.addWidget(QLabel("间距:"), row, 0)
        self.var_bond_space = QLineEdit("1.2")
        self.var_bond_space.setMaximumWidth(50)
        layout.addWidget(self.var_bond_space, row, 1)

        layout.addWidget(QLabel("半径:"), row, 2)
        self.var_bond_radius = QLineEdit("0.06")
        self.var_bond_radius.setMaximumWidth(50)
        layout.addWidget(self.var_bond_radius, row, 3)

        bond_btn_frame = QHBoxLayout()
        bond_btn_frame.setSpacing(4)
        self.btn_draw_bond = QPushButton("绘制")
        self.btn_draw_bond.setEnabled(False)
        self.btn_draw_bond.clicked.connect(self._draw_bond)
        bond_btn_frame.addWidget(self.btn_draw_bond)

        self.btn_undo_bond = QPushButton("撤销")
        self.btn_undo_bond.setEnabled(False)
        self.btn_undo_bond.setObjectName("SmallBtn")
        self.btn_undo_bond.clicked.connect(self._undo_bond)
        bond_btn_frame.addWidget(self.btn_undo_bond)

        self.btn_clear_bond = QPushButton("清除全部")
        self.btn_clear_bond.setEnabled(False)
        self.btn_clear_bond.setObjectName("SmallBtn")
        self.btn_clear_bond.clicked.connect(self._clear_bond)
        bond_btn_frame.addWidget(self.btn_clear_bond)

        layout.addLayout(bond_btn_frame, row, 4, 1, 2)

        for c in range(6):
            layout.setColumnStretch(c, 0)
        return grp

    def _apply_theme(self):
        self.setStyleSheet(LIGHT_QSS)

    def _append_log(self, msg):
        self.log_text.moveCursor(QTextCursor.End)
        self.log_text.insertPlainText(msg + "\n")
        self.log_text.moveCursor(QTextCursor.End)

    def _set_progress(self, msg):
        self.progress_label.setText(f"◆  {msg}")

    def _get_style_name(self):
        return self.var_style.currentText().strip()

    def _get_paths(self):
        vmd = self.var_vmd.text().strip()
        tachyon = os.path.join(os.path.dirname(vmd), "tachyon_WIN32.exe")
        return {"multiwfn": self.var_mw.text().strip(), "vmd": vmd, "tachyon": tachyon}

    def _save_paths(self):
        vmd = self.var_vmd.text().strip()
        tachyon = os.path.join(os.path.dirname(vmd), "tachyon_WIN32.exe")
        backend.save_config(self.var_mw.text().strip(), vmd, tachyon)

    def _get_params(self):
        style_name = self._get_style_name()
        representation = self.var_rep.currentText().strip()
        try:
            cpk_scale = float(self.var_scale.text().strip())
        except ValueError:
            cpk_scale = 1.0
        try:
            res_str = self.var_res.currentText().strip()
            w, h = res_str.split("x")
            resolution = (int(w), int(h))
        except (ValueError, AttributeError):
            resolution = (2000, 1500)
        shade_id = self.shade_group.checkedId()
        shade_mode = "full" if shade_id == 0 else "medium"

        keep_h_indices = None
        h_str = self.var_h_indices.text().strip()
        if h_str:
            try:
                keep_h_indices = [int(x.strip()) for x in h_str.split(",") if x.strip()]
            except ValueError:
                keep_h_indices = None
        else:
            if hasattr(self, '_h_filter_on') and self._h_filter_on:
                keep_h_indices = []

        return style_name, representation, cpk_scale, resolution, shade_mode, keep_h_indices

    def _cache_rep_style(self, style_name, representation, cpk_scale):
        s = backend.STYLES.get(style_name, backend.STYLES["sob_Gold"])
        atom_cpk = s.get("atom_cpk", "0.600000 0.400000 30.000000 30.000000")
        cpk_parts = atom_cpk.split()
        if len(cpk_parts) >= 2:
            try:
                scale_factor = float(cpk_scale)
                new_sphere = float(cpk_parts[0]) * scale_factor
                new_bond = float(cpk_parts[1]) * scale_factor
                scaled_cpk = f"{new_sphere:.6f} {new_bond:.6f}"
                if len(cpk_parts) >= 4:
                    scaled_cpk += f" {cpk_parts[2]} {cpk_parts[3]}"
                atom_cpk = scaled_cpk
            except (ValueError, IndexError):
                pass

        if representation == "CPK":
            self._current_rep_style = f"CPK {atom_cpk}"
            self._current_rep_material = "_stl_atom"
        elif representation == "Licorice":
            self._current_rep_style = "Licorice 0.2 12 12"
            self._current_rep_material = "_stl_bond"
        elif representation == "VDW":
            self._current_rep_style = f"VDW {atom_cpk.split()[0]} 12"
            self._current_rep_material = "_stl_atom"
        elif representation == "Bonds":
            self._current_rep_style = "Bonds 0.3 12"
            self._current_rep_material = "_stl_bond"
        else:
            self._current_rep_style = "Lines 1.0"
            self._current_rep_material = "_stl_atom"

    def _on_style_change(self, idx):
        if not self.vmd_port:
            return
        style_name = self.var_style.currentText().strip()
        if style_name in backend.STYLES:
            s = backend.STYLES[style_name]
            self._cache_rep_style(style_name, self.vmd_representation,
                                  self.vmd_cpk_scale)
            self.vmd_style_name = style_name
            self._send_vmd_cmd(f"mol modstyle 0 top {self._current_rep_style}")
            self._send_vmd_cmd(f"mol modmaterial 0 top {self._current_rep_material}")
            self._send_vmd_cmd("mol modcolor 0 top Element")
            self._send_vmd_cmd(f"color Element C {s.get('c_color', 'tan')}")
            self._send_vmd_cmd(f"color change rgb {s.get('c_color', 'tan')} {s.get('c_rgb', '0.7 0.56 0.36')}")
            self._append_log(f"已切换风格: {style_name}")

    def _browse_exe(self, which):
        path, _ = QFileDialog.getOpenFileName(
            self, f"选择 {which} 可执行文件", "", "可执行文件 (*.exe)")
        if path:
            if which == "multiwfn":
                self.var_mw.setText(path)
            elif which == "vmd":
                self.var_vmd.setText(path)

    def _browse_input(self):
        if self.mode_group.checkedId() == 0:
            path = QFileDialog.getExistingDirectory(self, "选择输入文件夹")
        else:
            path, _ = QFileDialog.getOpenFileName(
                self, "选择输入文件", "",
                "Gaussian Log (*.log);;所有文件 (*.*)")
        if path:
            self.var_path.setText(path)

    def _browse_out(self):
        path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if path:
            self.var_out.setText(path)

    def _run(self):
        if self.running:
            return
        path = self.var_path.text().strip()
        if not path:
            QMessageBox.warning(self, "提示", "请先选择文件或文件夹")
            return

        exe_paths = self._get_paths()
        if not os.path.exists(exe_paths["multiwfn"]):
            QMessageBox.warning(self, "路径错误",
                f"Multiwfn 未找到:\n{exe_paths['multiwfn']}")
            return
        if not os.path.exists(exe_paths["vmd"]):
            QMessageBox.warning(self, "路径错误",
                f"VMD 未找到:\n{exe_paths['vmd']}")
            return

        self._save_paths()

        files = (sorted(glob.glob(os.path.join(path, "*.log")))
                 if os.path.isdir(path) else [path])
        if not files:
            QMessageBox.warning(self, "提示", "未找到 .log 文件")
            return

        out = self.var_out.text().strip() or (
            path if os.path.isdir(path) else os.path.dirname(path))
        os.makedirs(out, exist_ok=True)

        style_name, representation, cpk_scale, resolution, shade_mode, keep_h_indices = self._get_params()
        auto_render = self.var_auto.isChecked()
        do_open = self.var_open.isChecked()

        self.running = True
        self._set_buttons_state("running")

        self.worker = LogWorker(
            files, out, style_name, representation, cpk_scale,
            resolution, shade_mode, keep_h_indices, auto_render,
            exe_paths, do_open)
        self.worker.log_signal.connect(self._append_log)
        self.worker.progress_signal.connect(self._set_progress)
        self.worker.finished_signal.connect(self._on_logs_done)
        self.worker.start()

    def _on_logs_done(self, auto_render, ok, total, preview_info):
        self.running = False
        self._set_buttons_state("idle")

        if not auto_render and preview_info:
            xyz_path, port, render_dir = preview_info[0]
            self.vmd_port = port
            self.vmd_render_dir = render_dir
            self.vmd_xyz_path = xyz_path
            style_name, representation, cpk_scale, resolution, shade_mode, _ = self._get_params()
            self.vmd_style_name = style_name
            self.vmd_representation = representation
            self.vmd_cpk_scale = str(cpk_scale)
            self.vmd_shade_mode = shade_mode
            self._cache_rep_style(style_name, representation, cpk_scale)
            self._append_log(
                "\n请在 VMD 中调整视角后，点击 [渲染当前视角]")
            self.btn_render.setEnabled(True)
            self.btn_draw_bond.setEnabled(True)
            self.btn_undo_bond.setEnabled(True)
            self.btn_clear_bond.setEnabled(True)
            self.btn_h_filter.setEnabled(True)
            self._h_filter_on = False

        if auto_render:
            self._append_log(f"\n全部完成 {ok}/{total}")
            self._set_progress(f"已完成: {ok}/{total}")
            if self.var_open.isChecked() and ok > 0:
                out = self.var_out.text().strip() or os.path.dirname(self.var_path.text().strip())
                os.startfile(out)

    def _preview(self):
        path = self.var_path.text().strip()
        if not path:
            QMessageBox.warning(self, "提示", "请先选择文件或文件夹")
            return

        log_file = path if os.path.isfile(path) else None
        if not log_file:
            out = self.var_out.text().strip()
            if out:
                logs = sorted(glob.glob(os.path.join(out, "*.log")))
                if logs:
                    log_file = logs[-1]
            if not log_file:
                QMessageBox.warning(self, "提示", "请选择 .log 文件")
                return

        out = self.var_out.text().strip() or (
            path if os.path.isdir(path) else os.path.dirname(path))
        exe_paths = self._get_paths()

        if not os.path.exists(exe_paths["multiwfn"]):
            QMessageBox.warning(self, "路径错误",
                f"Multiwfn 未找到:\n{exe_paths['multiwfn']}")
            return
        if not os.path.exists(exe_paths["vmd"]):
            QMessageBox.warning(self, "路径错误",
                f"VMD 未找到:\n{exe_paths['vmd']}")
            return

        style_name, representation, cpk_scale, resolution, shade_mode, keep_h_indices = self._get_params()

        self.vmd_style_name = style_name
        self.vmd_representation = representation
        self.vmd_cpk_scale = str(cpk_scale)
        self.vmd_shade_mode = shade_mode
        self._cache_rep_style(style_name, representation, cpk_scale)

        self._close_persist_sock()

        self._append_log(f"\n[1] Multiwfn: log -> xyz  ({os.path.basename(log_file)})")
        xyz = backend.log_to_xyz(log_file,
                                 multiwfn_exe=exe_paths["multiwfn"],
                                 work_dir=out)
        if not xyz:
            self._append_log("  xyz 转换失败！")
            return
        self._append_log(f"  -> {os.path.basename(xyz)}")

        self._append_log(f"[2] 启动 VMD 预览: {os.path.basename(xyz)}")
        self._append_log(f"样式: {style_name}  表示: {representation}")

        try:
            port, render_dir = backend.preview_mol(
                xyz, style_name=style_name,
                representation=representation, cpk_scale=str(cpk_scale),
                vmd_exe=exe_paths["vmd"],
                shade_mode=shade_mode, keep_h_indices=keep_h_indices)
            if port:
                self.vmd_port = port
                self.vmd_render_dir = render_dir
                self.vmd_xyz_path = xyz
                self.btn_render.setEnabled(True)
                self.btn_draw_bond.setEnabled(True)
                self.btn_undo_bond.setEnabled(True)
                self.btn_clear_bond.setEnabled(True)
                self.btn_h_filter.setEnabled(True)
                self._h_filter_on = False
                self._append_log(f"VMD 已启动 (端口 {port})，等待操作...")
            else:
                self._append_log("VMD 启动失败")
        except Exception as e:
            self._append_log(f"VMD 启动错误: {e}")

    def _render_view(self):
        if not self.vmd_port or not self.vmd_render_dir:
            QMessageBox.warning(self, "提示",
                "请先点击 [预览] 打开 VMD")
            return

        out = self.var_out.text().strip()
        if out and not os.path.isdir(out):
            os.makedirs(out, exist_ok=True)

        style_name, _, _, resolution, shade_mode, _ = self._get_params()
        exe_paths = self._get_paths()

        output_png = None
        if self.vmd_xyz_path and out:
            stem = os.path.splitext(os.path.basename(self.vmd_xyz_path))[0]
            output_png = os.path.join(out, f"{stem}.png")

        self.btn_render.setEnabled(False)
        self.render_worker = RenderWorker(
            self.vmd_port, self.vmd_render_dir, output_png,
            exe_paths["tachyon"], resolution, style_name, shade_mode)
        self.render_worker.log_signal.connect(self._append_log)
        self.render_worker.finished_signal.connect(self._on_render_done)
        self.render_worker.start()

    def _on_render_done(self, png_path):
        self.btn_render.setEnabled(True)
        if png_path and os.path.exists(png_path):
            os.startfile(png_path)

    def _stop(self):
        self.running = False
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.stop()
        self.btn_stop.setEnabled(False)

    def _set_buttons_state(self, state):
        if state == "running":
            self.btn_run.setEnabled(False)
            self.btn_render.setEnabled(False)
            self.btn_stop.setEnabled(True)
        else:
            self.btn_run.setEnabled(True)
            self.btn_preview.setEnabled(True)
            self.btn_stop.setEnabled(False)

    def _send_vmd_cmd(self, cmd):
        sock = getattr(self, '_vmd_persist_sock', None)
        if sock is None:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect(("127.0.0.1", self.vmd_port))
                self._vmd_persist_sock = sock
            except Exception:
                return ""
        try:
            sock.sendall((cmd + "\n").encode("utf-8"))
            time.sleep(0.05)
            resp = b""
            sock.settimeout(1)
            try:
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    resp += chunk
                    if b"\n" in resp:
                        break
            except socket.timeout:
                pass
            return resp.decode("utf-8", errors="replace").strip()
        except Exception:
            self._close_persist_sock()
            return ""

    def _close_persist_sock(self):
        sock = getattr(self, '_vmd_persist_sock', None)
        if sock:
            try:
                sock.close()
            except Exception:
                pass
            self._vmd_persist_sock = None

    def _toggle_h_filter(self):
        if not self.vmd_port:
            self._append_log("请先点击预览按钮启动 VMD")
            return

        current_text = self.btn_h_filter.text()
        if current_text == "隐藏所有氢原子":
            self.btn_h_filter.setText("显示所有氢原子")
            self._h_filter_on = True
            h_str = self.var_h_indices.text().strip()
            if h_str:
                try:
                    keep_indices = [int(x.strip()) for x in h_str.split(",") if x.strip()]
                    idx_str = " ".join(map(str, keep_indices))
                    sel_str = f"not element H or (element H and index {idx_str})"
                except ValueError:
                    sel_str = "not element H"
            else:
                sel_str = "not element H"
            cmd = (
                f'set _h_sel [atomselect top "{sel_str}"];'
                f' if {{[$_h_sel num] > 0}} {{'
                f'   $_h_sel writepdb _temp_hfilter.pdb;'
                f'   mol delete top;'
                f'   mol new _temp_hfilter.pdb type pdb waitfor all;'
                f'   file delete _temp_hfilter.pdb;'
                f'   mol modstyle 0 top {self._current_rep_style};'
                f'   mol modmaterial 0 top {self._current_rep_material};'
                f'   mol modcolor 0 top Element'
                f' }};'
                f' $_h_sel delete'
            )
            self._send_vmd_cmd(cmd)
            self._append_log("[隐藏H] 已隐藏氢原子")
        else:
            self.btn_h_filter.setText("隐藏所有氢原子")
            self._h_filter_on = False
            if self.vmd_xyz_path:
                xyz_name = os.path.basename(self.vmd_xyz_path)
                if self.vmd_render_dir:
                    xyz_path = os.path.join(self.vmd_render_dir, xyz_name)
                else:
                    xyz_path = os.path.abspath(self.vmd_xyz_path)
                self._send_vmd_cmd("mol delete top")
                self._send_vmd_cmd(
                    f"mol new {{{xyz_path}}} type xyz first 0 last 0 step 1 waitfor all")
                self._send_vmd_cmd(f"mol modstyle 0 top {self._current_rep_style}")
                self._send_vmd_cmd(f"mol modmaterial 0 top {self._current_rep_material}")
                self._send_vmd_cmd("mol modcolor 0 top Element")
                s = backend.STYES.get(self.vmd_style_name, backend.STYES["sob_Gold"])
                self._send_vmd_cmd(f"color Element C {s.get('c_color', 'tan')}")
                self._send_vmd_cmd(f"color change rgb {s.get('c_color', 'tan')} {s.get('c_rgb', '0.7 0.56 0.36')}")
                self._send_vmd_cmd("display distance -8.0")
                self._send_vmd_cmd("display height 10")
            self._append_log("[隐藏H] 已恢复氢原子")

    def _draw_bond(self):
        if not self.vmd_port:
            QMessageBox.warning(self, "提示",
                "请先点击 [预览] 打开 VMD")
            return
        a1 = self.var_bond_atom1.text().strip()
        a2 = self.var_bond_atom2.text().strip()
        if not a1 or not a2:
            QMessageBox.warning(self, "提示", "请输入两个原子编号")
            return

        bond_color_map = {
            "黑色": "black", "灰色": "gray", "青色": "cyan", "黄色": "yellow",
            "红色": "red", "蓝色": "blue", "绿色": "green",
            "白色": "white", "橙色": "orange", "紫色": "purple"}
        bond_type_map = {
            "虚线(pymol)": "pymol", "圆点(dots)": "dots",
            "实线圆柱": "cylinder", "球体": "sphere",
            "圆锥": "cone", "线条": "line"}
        bond_mat_map = {
            "不透明": "Opaque", "50%透明": "HalfTransparent",
            "透明": "Transparent"}

        color = bond_color_map.get(self.var_bond_color.currentText(), "gray")
        btype = bond_type_map.get(self.var_bond_type.currentText(), "dots")
        mat = bond_mat_map.get(self.var_bond_mat.currentText(), "HalfTransparent")
        nbars = self.var_bond_nbars.text().strip() or "10"
        space = self.var_bond_space.text().strip() or "1.2"
        radius = self.var_bond_radius.text().strip() or "0.06"

        if btype == "cylinder":
            cmd = (f"draw_bond -mol1 top -index1 {a1} -mol2 top -index2 {a2} "
                   f"-color {color} -h_type {btype} -h_radius {radius} -mat {mat}")
        else:
            cmd = (f"draw_bond -mol1 top -index1 {a1} -mol2 top -index2 {a2} "
                   f"-h_nbars {nbars} -h_space {space} -h_radius {radius} "
                   f"-color {color} -h_type {btype} -mat {mat}")
        resp = self._send_vmd_cmd(cmd)
        if resp and "ERROR" not in resp:
            self._append_log(f"[绘制键] 原子{a1}-{a2} {color} {btype} {mat}")
            self.btn_undo_bond.setEnabled(True)
        else:
            self._append_log("[绘制键] 失败")

    def _undo_bond(self):
        resp = self._send_vmd_cmd("draw_bond_undo")
        if resp and "ERROR" not in resp:
            self._append_log("[键] 已撤销")
        else:
            self._append_log("[键] 撤销失败")

    def _clear_bond(self):
        resp = self._send_vmd_cmd("draw_bond_clear")
        if resp and "ERROR" not in resp:
            self._append_log("[键] 已清除全部")
            self.btn_undo_bond.setEnabled(False)
        else:
            self._append_log("[键] 清除失败")

    def closeEvent(self, event):
        self._close_persist_sock()
        super().closeEvent(event)


def main():
    if len(sys.argv) > 1:
        import argparse
        p = argparse.ArgumentParser(
            description="Multiwfn + VMD/Tachyon 分子结构渲染 v1.2 (Gaussian log)")
        p.add_argument("input", help="log 文件或文件夹")
        p.add_argument("--style", default="sob_Gold",
                       choices=list(backend.STYLES.keys()), help="渲染样式")
        p.add_argument("--rep", default="CPK",
                       choices=list(backend.REPRESENTATIONS.keys()), help="分子表示方式")
        p.add_argument("--scale", type=float, default=0.6, help="CPK/VDW 缩放比")
        p.add_argument("--res", default="2000,1500", help="分辨率 宽,高")
        p.add_argument("--out", default=None)
        a = p.parse_args()

        files = sorted(glob.glob(os.path.join(a.input, "*.log"))) if os.path.isdir(a.input) else [a.input]
        out = a.out or (os.path.dirname(a.input) if os.path.isfile(a.input) else a.input)
        os.makedirs(out, exist_ok=True)

        w, h = [int(x) for x in a.res.split(",")]

        for i, f in enumerate(files):
            print(f"[{i+1}/{len(files)}] {os.path.basename(f)}")
            xyz = backend.log_to_xyz(f, work_dir=out)
            if not xyz:
                print("  log->xyz 失败")
                continue
            print(f"  xyz: {os.path.basename(xyz)}")
            stem = os.path.splitext(os.path.basename(f))[0]
            png = os.path.join(out, f"{stem}.png")
            result = backend.render_mol_auto(xyz, output_png=png,
                                             style_name=a.style,
                                             representation=a.rep,
                                             cpk_scale=str(a.scale),
                                             resolution=(w, h))
            if result:
                print(f"  OK: {os.path.basename(result)}")
            else:
                print(f"  渲染失败")
    else:
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        window = LogRenderApp()
        window.show()
        sys.exit(app.exec_())


if __name__ == "__main__":
    main()
