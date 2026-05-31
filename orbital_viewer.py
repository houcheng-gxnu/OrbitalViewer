#!/usr/bin/env python3
"""
fchk Orbital Isosurface Visualization Tool v5.1 (PyQt Edition)
Multiwfn (fchk -> cube) + VMD (Preview + Tachyon Rendering) + Tachyon (scene -> BMP/PNG)

PyQt5 rewrite with clean light sci-fi UI theme.
All backend logic imported from fchk_orbital.py.
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
    QFrame, QSplitter, QScrollArea, QGridLayout, QSizePolicy,
    QSlider, QTabWidget,
)
from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import (
    QFont, QColor, QPalette, QFontDatabase, QTextCursor, QKeySequence,
    QLinearGradient, QBrush, QPainter, QPixmap, QIcon,
)

# ── Import backend from original module ──────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fchk_orbital as backend


# ── Light Sci-Fi Theme Stylesheet ──────────────────────
LIGHT_QSS = """
/* ── Global ── */
QMainWindow {
    background-color: #E4EAF2;
}

QWidget {
    font-family: "Segoe UI", "Microsoft YaHei", "Consolas", sans-serif;
    font-size: 9pt;
    color: #2C3E50;
}

/* ── Group Box ── */
QGroupBox {
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    margin-top: 16px;
    padding: 18px 12px 12px 12px;
    background-color: #FFFFFF;
    font-weight: bold;
    font-size: 10pt;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 16px;
    padding: 2px 12px 2px 12px;
    color: #FFFFFF;
    background-color: #1565C0;
    border-radius: 4px;
    font-size: 9pt;
}

/* ── Labels ── */
QLabel {
    color: #4A5568;
    padding: 1px 0px;
}

QLabel#TitleLabel {
    color: #0D47A1;
    font-size: 16pt;
    font-weight: bold;
    padding: 6px 8px 2px 8px;
    qproperty-alignment: AlignCenter;
}

QLabel#SubTitleLabel {
    color: #5C6BC0;
    font-size: 8.5pt;
    padding: 0px 8px 8px 8px;
    qproperty-alignment: AlignCenter;
}

QLabel#ProgressLabel {
    color: #1565C0;
    font-size: 9pt;
    font-weight: bold;
    padding: 5px 12px;
    background-color: #EEF2FF;
    border: 1px solid #C5CAE9;
    border-radius: 4px;
}

QLabel#HintLabel {
    color: #7986CB;
    font-size: 8pt;
    padding: 1px 4px;
}

/* ── Line Edit ── */
QLineEdit {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 5px;
    padding: 5px 10px;
    color: #2C3E50;
    selection-background-color: #1E88E5;
    selection-color: #FFFFFF;
}

QLineEdit:focus {
    border: 1px solid #1E88E5;
    background-color: #F8FAFE;
}

QLineEdit:disabled {
    background-color: #F1F5F9;
    color: #94A3B8;
    border: 1px solid #E2E8F0;
}

/* ── Combo Box ── */
QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 5px;
    padding: 5px 10px;
    color: #2C3E50;
    min-width: 80px;
}

QComboBox:focus {
    border: 1px solid #1E88E5;
}

QComboBox:hover {
    border: 1px solid #5C6BC0;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 22px;
    border-left: 1px solid #E2E8F0;
    border-top-right-radius: 5px;
    border-bottom-right-radius: 5px;
    background-color: #F8FAFE;
}

QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 5px;
    color: #2C3E50;
    selection-background-color: #E3F2FD;
    selection-color: #1565C0;
    outline: none;
}

QComboBox QAbstractItemView::item:hover {
    background-color: #E8EAF6;
    color: #1A237E;
}

/* ── Radio Button ── */
QRadioButton {
    color: #4A5568;
    spacing: 6px;
    padding: 3px 6px;
}

QRadioButton::indicator {
    width: 15px;
    height: 15px;
    border-radius: 8px;
    border: 2px solid #A0AEC0;
    background-color: #FFFFFF;
}

QRadioButton::indicator:checked {
    border: 2px solid #1E88E5;
    background-color: #1E88E5;
}

QRadioButton::indicator:hover {
    border: 2px solid #5C6BC0;
}

QRadioButton:checked {
    color: #1565C0;
    font-weight: bold;
}

/* ── Check Box ── */
QCheckBox {
    color: #4A5568;
    spacing: 6px;
    padding: 3px 6px;
}

QCheckBox::indicator {
    width: 15px;
    height: 15px;
    border-radius: 3px;
    border: 2px solid #A0AEC0;
    background-color: #FFFFFF;
}

QCheckBox::indicator:checked {
    border: 2px solid #1E88E5;
    background-color: #1E88E5;
}

QCheckBox::indicator:hover {
    border: 2px solid #5C6BC0;
}

QCheckBox:checked {
    color: #1565C0;
}

/* ── Push Button ── */
QPushButton {
    background-color: #F8FAFE;
    border: 1px solid #CBD5E1;
    border-radius: 5px;
    padding: 6px 16px;
    color: #2C3E50;
    font-weight: bold;
    font-size: 9pt;
}

QPushButton:hover {
    background-color: #E3F2FD;
    border: 1px solid #1E88E5;
    color: #1565C0;
}

QPushButton:pressed {
    background-color: #BBDEFB;
    border: 1px solid #1565C0;
}

QPushButton:disabled {
    background-color: #F1F5F9;
    border: 1px solid #E2E8F0;
    color: #94A3B8;
}

QPushButton#PrimaryBtn {
    background-color: #1565C0;
    border: 1px solid #0D47A1;
    color: #FFFFFF;
    font-size: 10pt;
    padding: 8px 20px;
}

QPushButton#PrimaryBtn:hover {
    background-color: #1E88E5;
    border: 1px solid #1565C0;
    color: #FFFFFF;
}

QPushButton#PrimaryBtn:pressed {
    background-color: #0D47A1;
}

QPushButton#RenderBtn {
    background-color: #00897B;
    border: 1px solid #00695C;
    color: #FFFFFF;
    font-size: 10pt;
    padding: 8px 20px;
}

QPushButton#RenderBtn:hover {
    background-color: #26A69A;
    border: 1px solid #00897B;
    color: #FFFFFF;
}

QPushButton#RenderBtn:pressed {
    background-color: #00695C;
}

QPushButton#StopBtn {
    background-color: #FFFFFF;
    border: 1px solid #E53935;
    color: #E53935;
    font-size: 10pt;
    padding: 8px 20px;
}

QPushButton#StopBtn:hover {
    background-color: #FFEBEE;
    border: 1px solid #EF5350;
    color: #D32F2F;
}

QPushButton#StopBtn:pressed {
    background-color: #FFCDD2;
}

QPushButton#SmallBtn {
    padding: 3px 10px;
    font-size: 8pt;
    min-width: 34px;
}

QPushButton#SmallBtn:hover {
    background-color: #E3F2FD;
    border: 1px solid #1E88E5;
    color: #1565C0;
}

/* ── Text Edit (Log) ── */
QTextEdit {
    background-color: #F5F6FA;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 8px 10px;
    color: #1E293B;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 8.5pt;
    selection-background-color: #BBDEFB;
    selection-color: #0D47A1;
}

QTextEdit:focus {
    border: 1px solid #1E88E5;
}

QScrollBar:vertical {
    background-color: #F1F5F9;
    width: 10px;
    margin: 0;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #CBD5E1;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #1E88E5;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
    background: none;
}

QScrollBar:horizontal {
    background-color: #F1F5F9;
    height: 10px;
    margin: 0;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background-color: #CBD5E1;
    border-radius: 5px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #1E88E5;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
    background: none;
}

/* ── Frame separator ── */
QFrame#Separator {
    background-color: #CBD5E1;
    max-height: 1px;
}

/* ── Scroll Area ── */
QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

/* ── Slider ── */
QSlider::groove:horizontal {
    border: 1px solid #CBD5E1;
    height: 8px;
    background-color: #F1F5F9;
    border-radius: 4px;
}

QSlider::sub-page:horizontal {
    background-color: #1E88E5;
    border-radius: 4px;
}

QSlider::handle:horizontal {
    background-color: #FFFFFF;
    border: 2px solid #1E88E5;
    width: 18px;
    height: 18px;
    margin: -6px 0;
    border-radius: 9px;
}

QSlider::handle:horizontal:hover {
    background-color: #E3F2FD;
    border: 2px solid #1565C0;
}

QSlider::handle:horizontal:pressed {
    background-color: #BBDEFB;
    border: 2px solid #0D47A1;
}

QSlider:disabled {
    color: #94A3B8;
}

QSlider::groove:horizontal:disabled {
    background-color: #F1F5F9;
    border: 1px solid #E2E8F0;
}

QSlider::handle:horizontal:disabled {
    background-color: #F1F5F9;
    border: 2px solid #E2E8F0;
}

/* ── Tooltip ── */
QToolTip {
    background-color: #FFFFFF;
    border: 1px solid #1E88E5;
    border-radius: 4px;
    padding: 5px 10px;
    color: #2C3E50;
    font-size: 8.5pt;
}

/* ── Tab Widget ── */
QTabWidget::pane {
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    background-color: #FFFFFF;
    padding: 8px;
}

QTabBar::tab {
    background-color: #F1F5F9;
    border: 1px solid #CBD5E1;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 28px;
    margin-right: 3px;
    min-width: 80px;
    color: #4A5568;
    font-weight: bold;
    font-size: 9pt;
}

QTabBar::tab:selected {
    background-color: #FFFFFF;
    color: #1565C0;
    border-bottom: 2px solid #1E88E5;
}

QTabBar::tab:hover:!selected {
    background-color: #E3F2FD;
    color: #1565C0;
}

QTabBar::tab:disabled {
    color: #94A3B8;
    background-color: #F1F5F9;
}
"""


# ── Titled Panel ─────────────────────────────────────
class SciFiGroupBox(QGroupBox):
    """Custom group box with sci-fi style corner decorations."""

    def __init__(self, title, parent=None):
        super().__init__(title, parent)


# ── Worker Threads ───────────────────────────────────────
class CubeWorker(QThread):
    """Background worker for cube generation."""
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, int, int, list)

    def __init__(self, files, out_dir, orbitals, iso, grid, style_name,
                 resolution, shade_mode, auto_render, exe_paths, do_open):
        super().__init__()
        self.files = files
        self.out_dir = out_dir
        self.orbitals = orbitals
        self.iso = iso
        self.grid = grid
        self.style_name = style_name
        self.resolution = resolution
        self.shade_mode = shade_mode
        self.auto_render = auto_render
        self.exe_paths = exe_paths
        self.do_open = do_open
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        total = len(self.files)
        is_multi = len(self.orbitals) > 1
        orbital = self.orbitals[0] if self.orbitals else ""

        self.log_signal.emit(f"{total} files -> {self.out_dir}")
        if is_multi:
            self.log_signal.emit(
                f"Orbitals=[{','.join(self.orbitals)}]  iso={self.iso}  "
                f"grid={self.grid}  Style={self.style_name}  "
                f"res={self.resolution[0]}x{self.resolution[1]}")
        else:
            self.log_signal.emit(
                f"Orbital={orbital}  iso={self.iso}  grid={self.grid}  "
                f"Style={self.style_name}  res={self.resolution[0]}x{self.resolution[1]}")
        if self.auto_render:
            self.log_signal.emit("Mode: Auto render (no preview)")
        else:
            self.log_signal.emit("Mode: Generate cube -> Manual preview -> Render")
        self.log_signal.emit("=" * 50)

        ok = 0
        cubes = []
        t_total = time.time()
        for i, fchk in enumerate(self.files):
            if not self._running:
                self.log_signal.emit("Stopped")
                break
            name = os.path.basename(fchk)
            self.progress_signal.emit(f"[{i+1}/{total}] {name}")
            self.log_signal.emit(f"\n[{i+1}/{total}] {name}")

            t0 = time.time()
            cube_result = None
            if is_multi:
                results = backend.gen_multi_cubes(
                    fchk, self.orbitals,
                    grid_quality=int(self.grid), work_dir=self.out_dir,
                    multiwfn_exe=self.exe_paths["multiwfn"])
                dt = time.time() - t0
                if results:
                    for cube_path, orb_name in results:
                        self.log_signal.emit(
                            f"  cube OK ({orb_name}) -> {os.path.basename(cube_path)}")
                        cubes.append((cube_path, orb_name))
                    ok += 1
                    cube_result = results[0][0] if results else None
                else:
                    self.log_signal.emit(f"  Cube generation failed ({dt:.1f}s)")
            else:
                result = backend.gen_cube(
                    fchk, orbital=orbital,
                    grid_quality=int(self.grid), work_dir=self.out_dir,
                    multiwfn_exe=self.exe_paths["multiwfn"])
                cube_result = result
                dt = time.time() - t0
                if not result:
                    self.log_signal.emit(f"  Cube failed ({dt:.1f}s)")
                    continue
                self.log_signal.emit(
                    f"  cube OK ({dt:.1f}s) -> {os.path.basename(result)}")
                cubes.append(result)
                ok += 1

            if self.auto_render and cube_result:
                t0 = time.time()
                try:
                    png = self._fchk_to_png_name(fchk)
                    backend.render_cube_auto(
                        cube_result, output_png=png, isovalue=self.iso,
                        style_name=self.style_name, resolution=self.resolution,
                        vmd_exe=self.exe_paths["vmd"],
                        tachyon_exe=self.exe_paths["tachyon"],
                        shade_mode=self.shade_mode)
                    dt = time.time() - t0
                    self.log_signal.emit(f"  PNG: {os.path.basename(png)} ({dt:.1f}s)")
                except Exception as e:
                    self.log_signal.emit(f"  Render error: {e}")

        elapsed = time.time() - t_total
        self.log_signal.emit(
            f"\nCube generation completed: {ok}/{total}, elapsed {elapsed:.1f}s")
        self.finished_signal.emit(self.auto_render, ok, total, cubes)

    def _fchk_to_png_name(self, fchk_path):
        orbital = ",".join(self.orbitals) if len(self.orbitals) > 1 else self.orbitals[0]
        stem = os.path.splitext(os.path.basename(fchk_path))[0]
        return os.path.join(self.out_dir, f"{stem}_MO{orbital}.png")


class RenderWorker(QThread):
    """Background worker for Tachyon rendering."""
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str)

    def __init__(self, port, render_dir, output_png, tachyon_exe, resolution,
                 style_name, shade_mode, trans_raster, threads):
        super().__init__()
        self.port = port
        self.render_dir = render_dir
        self.output_png = output_png
        self.tachyon_exe = tachyon_exe
        self.resolution = resolution
        self.style_name = style_name
        self.shade_mode = shade_mode
        self.trans_raster = trans_raster
        self.threads = threads

    def run(self):
        self.log_signal.emit(f"\nRendering current view (Style: {self.style_name})...")
        t0 = time.time()
        try:
            png = backend.render_current_view(
                self.port, self.render_dir,
                output_png=self.output_png,
                tachyon_exe=self.tachyon_exe,
                resolution=self.resolution,
                style_name=self.style_name,
                shade_mode=self.shade_mode,
                trans_raster=self.trans_raster,
                threads=self.threads,
            )
            dt = time.time() - t0
            if png:
                self.log_signal.emit(
                    f"Render completed ({dt:.1f}s) -> {os.path.basename(png)}")
                self.finished_signal.emit(png)
            else:
                self.log_signal.emit(f"Render failed ({dt:.1f}s)")
                self.finished_signal.emit("")
        except Exception as e:
            self.log_signal.emit(f"Render error: {e}")
            self.finished_signal.emit("")


# ── Main Application Window ──────────────────────────────
class OrbitalVisApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Orbital Isosurface Visualization v5.1 — Multiwfn + VMD/Tachyon [PyQt Edition]")
        self.resize(920, 780)
        self.setMinimumSize(840, 680)

        self.paths = backend.load_config()
        self.running = False
        self.vmd_port = None
        self.vmd_render_dir = None
        self.vmd_cube_path = None
        self._vmd_persist_sock = None
        self.vmd_multi_cubes = None
        self.current_iso = 0.05
        self.current_opacity = None
        self.iso_step = 0.005
        self.opacity_step = 0.05

        self._current_cubes = []
        self._current_orbitals = []

        self._setup_ui()
        self._setup_shortcuts()
        self._apply_theme()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(12, 8, 12, 10)
        main_layout.setSpacing(6)

        title_label = QLabel("\u25c8  ORBITAL ISOSURFACE VISUALIZATION  \u25c8")
        title_label.setObjectName("TitleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        sub_label = QLabel("Multiwfn + VMD + Tachyon  |  v5.1 PyQt Light Edition")
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
        self.tabs.addTab(tab_setup, "\U0001f4c1  Setup")

        tab_params = QWidget()
        tab_params_layout = QVBoxLayout(tab_params)
        tab_params_layout.setContentsMargins(4, 4, 4, 4)
        tab_params_layout.setSpacing(6)
        tab_params_layout.addWidget(self._build_orbital_panel())
        tab_params_layout.addWidget(self._build_render_params_panel())
        tab_params_layout.addStretch()
        self.tabs.addTab(tab_params, "\U0001f3a8  Orbital & Render")

        tab_preview = QWidget()
        tab_preview_layout = QVBoxLayout(tab_preview)
        tab_preview_layout.setContentsMargins(4, 4, 4, 4)
        tab_preview_layout.setSpacing(6)
        tab_preview_layout.addWidget(self._build_buttons_panel())
        tab_preview_layout.addWidget(self._build_live_panel())
        tab_preview_layout.addStretch()
        self.tabs.addTab(tab_preview, "\u25b6\ufe0f  Preview")

        tab_tools = QWidget()
        tab_tools_layout = QVBoxLayout(tab_tools)
        tab_tools_layout.setContentsMargins(4, 4, 4, 4)
        tab_tools_layout.setSpacing(6)
        tab_tools_layout.addWidget(self._build_hydrogen_panel())
        tab_tools_layout.addWidget(self._build_draw_bond_panel())
        tab_tools_layout.addStretch()
        self.tabs.addTab(tab_tools, "\U0001f6e0\ufe0f  Tools")

        main_layout.addWidget(self.tabs, stretch=3)

        self.progress_label = QLabel("\u25c6  Ready")
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
        grp = SciFiGroupBox("SOFTWARE PATHS")
        layout = QGridLayout(grp)
        layout.setVerticalSpacing(4)
        layout.setHorizontalSpacing(6)

        # Multiwfn
        layout.addWidget(QLabel("Multiwfn:"), 0, 0)
        self.var_mw = QLineEdit(self.paths["multiwfn"])
        self.var_mw.setPlaceholderText("Path to Multiwfn.exe")
        layout.addWidget(self.var_mw, 0, 1)
        btn = QPushButton("Browse")
        btn.setObjectName("SmallBtn")
        btn.clicked.connect(lambda: self._browse_exe("multiwfn"))
        layout.addWidget(btn, 0, 2)

        # VMD
        layout.addWidget(QLabel("VMD:"), 1, 0)
        self.var_vmd = QLineEdit(self.paths["vmd"])
        self.var_vmd.setPlaceholderText("Path to vmd.exe")
        layout.addWidget(self.var_vmd, 1, 1)
        btn = QPushButton("Browse")
        btn.setObjectName("SmallBtn")
        btn.clicked.connect(lambda: self._browse_exe("vmd"))
        layout.addWidget(btn, 1, 2)

        layout.setColumnStretch(1, 1)
        return grp

    def _build_input_panel(self):
        grp = SciFiGroupBox("INPUT")
        layout = QHBoxLayout(grp)
        layout.setSpacing(6)

        self.mode_group = QButtonGroup(self)
        rb_folder = QRadioButton("Folder")
        rb_file = QRadioButton("Single File")
        self.mode_group.addButton(rb_folder, 0)
        self.mode_group.addButton(rb_file, 1)
        rb_file.setChecked(True)
        layout.addWidget(rb_folder)
        layout.addWidget(rb_file)

        self.var_path = QLineEdit()
        self.var_path.setPlaceholderText("Select .fchk file or folder...")
        layout.addWidget(self.var_path, stretch=1)
        btn = QPushButton("Browse")
        btn.clicked.connect(self._browse_input)
        layout.addWidget(btn)

        return grp

    def _build_orbital_panel(self):
        grp = SciFiGroupBox("ORBITAL SELECTION")
        layout = QGridLayout(grp)
        layout.setVerticalSpacing(4)
        layout.setHorizontalSpacing(6)

        row = 0
        # Orbital(s)
        layout.addWidget(QLabel("Orbital(s):"), row, 0)
        self.var_orbital = QLineEdit("h")
        self.var_orbital.setMaximumWidth(220)
        layout.addWidget(self.var_orbital, row, 1)
        hint = QLabel("comma separated, e.g.: h,l,h-1,l+1")
        hint.setObjectName("HintLabel")
        layout.addWidget(hint, row, 2, 1, 3)

        row += 1
        layout.addWidget(QLabel("Isosurface:"), row, 0)
        self.var_iso = QLineEdit("0.05")
        self.var_iso.setMaximumWidth(70)
        layout.addWidget(self.var_iso, row, 1)

        layout.addWidget(QLabel("Grid:"), row, 2)
        self.var_grid = QComboBox()
        self.var_grid.addItems(["1", "2", "3"])
        self.var_grid.setCurrentIndex(1)
        self.var_grid.setMaximumWidth(60)
        layout.addWidget(self.var_grid, row, 3)
        hint = QLabel("1=low 2=medium 3=high")
        hint.setObjectName("HintLabel")
        layout.addWidget(hint, row, 4)

        # Naming rules
        row += 1
        rules = (
            "<b>Orbital Naming Rules:</b><br>"
            "• Closed-shell: h=HOMO, l=LUMO, h-1=HOMO-1, number=orbital index<br>"
            "• Open-shell: positive=alpha orbital, negative=beta orbital<br>"
            "• Open-shell symbols: ha=alpha HOMO, hb=beta HOMO, la=alpha LUMO, lb=beta LUMO<br>"
            "• Examples: hb-5=beta HOMO-5, la+3=alpha LUMO+3, -131=beta orbital 131"
        )
        rule_label = QLabel(rules)
        rule_label.setStyleSheet("color: #555; font-size: 8.5pt;")
        rule_label.setWordWrap(True)
        layout.addWidget(rule_label, row, 0, 1, 5)

        for c in range(5):
            layout.setColumnStretch(c, 0)
        layout.setColumnStretch(1, 1)
        return grp

    def _build_render_params_panel(self):
        grp = SciFiGroupBox("RENDER PARAMETERS")
        rlayout = QGridLayout(grp)
        rlayout.setVerticalSpacing(4)
        rlayout.setHorizontalSpacing(6)

        rlayout.addWidget(QLabel("Style:"), 0, 0)
        self.var_style = QComboBox()
        self.var_style.setIconSize(QtCore.QSize(30, 13))
        self.var_style.setMinimumWidth(420)
        for name in backend.STYLES:
            icon = self._make_style_icon(backend.STYLES[name])
            self.var_style.addItem(icon, f"  {name}")
        self.var_style.setCurrentIndex(0)
        rlayout.addWidget(self.var_style, 0, 1, 1, 4)

        rlayout.addWidget(QLabel("Resolution:"), 1, 0)
        self.var_res = QComboBox()
        self.var_res.addItems(["2000x1500", "1200x900", "3000x2250"])
        self.var_res.setCurrentIndex(0)
        self.var_res.setMaximumWidth(120)
        rlayout.addWidget(self.var_res, 1, 1)

        rlayout.addWidget(QLabel("Shading:"), 1, 2)
        shade_frame = QHBoxLayout()
        shade_frame.setSpacing(4)
        self.shade_group = QButtonGroup(self)
        rb_full = QRadioButton("Full")
        rb_medium = QRadioButton("Medium")
        self.shade_group.addButton(rb_full, 0)
        self.shade_group.addButton(rb_medium, 1)
        rb_full.setChecked(True)
        shade_frame.addWidget(rb_full)
        shade_frame.addWidget(rb_medium)
        rlayout.addLayout(shade_frame, 1, 3, 1, 2)

        mode_frame = QHBoxLayout()
        mode_frame.setSpacing(8)
        self.var_auto = QCheckBox("Auto render (no preview, batch mode)")
        self.var_open = QCheckBox("Open folder after completion")
        mode_frame.addWidget(self.var_auto)
        mode_frame.addWidget(self.var_open)
        mode_frame.addStretch()
        rlayout.addLayout(mode_frame, 2, 0, 1, 5)

        tachy_frame = QHBoxLayout()
        tachy_frame.setSpacing(8)
        self.var_trans_raster = QCheckBox("-trans_raster3d")
        self.var_trans_raster.setChecked(True)
        tachy_frame.addWidget(self.var_trans_raster)
        tachy_frame.addWidget(QLabel("Threads:"))
        self.var_threads = QComboBox()
        self.var_threads.addItems(["1", "2", "4", "8", "16", "28"])
        self.var_threads.setCurrentIndex(2)
        self.var_threads.setMaximumWidth(60)
        tachy_frame.addWidget(self.var_threads)
        tachy_frame.addStretch()
        rlayout.addLayout(tachy_frame, 3, 0, 1, 5)

        for c in range(5):
            rlayout.setColumnStretch(c, 0)
        rlayout.setColumnStretch(1, 1)
        return grp

    def _build_output_panel(self):
        grp = SciFiGroupBox("OUTPUT DIRECTORY")
        layout = QHBoxLayout(grp)
        layout.setSpacing(6)

        hint = QLabel("(default: same as input)")
        hint.setObjectName("HintLabel")
        layout.addWidget(hint)

        self.var_out = QLineEdit()
        self.var_out.setPlaceholderText("Output directory...")
        layout.addWidget(self.var_out, stretch=1)
        btn = QPushButton("Browse")
        btn.clicked.connect(self._browse_out)
        layout.addWidget(btn)

        return grp

    def _build_buttons_panel(self):
        grp = SciFiGroupBox("ACTIONS")
        layout = QHBoxLayout(grp)
        layout.setSpacing(8)

        btn_min_width = 160

        self.btn_run = QPushButton("◆  Generate Cube")
        self.btn_run.setObjectName("PrimaryBtn")
        self.btn_run.setMinimumWidth(btn_min_width)
        self.btn_run.clicked.connect(self._run_cubes)
        layout.addWidget(self.btn_run)

        self.btn_preview = QPushButton("◇  Preview (Single)")
        self.btn_preview.setEnabled(False)
        self.btn_preview.setMinimumWidth(btn_min_width)
        self.btn_preview.clicked.connect(self._preview_single)
        layout.addWidget(self.btn_preview)

        self.btn_preview_multi = QPushButton("◇  Preview (Multi)")
        self.btn_preview_multi.setEnabled(False)
        self.btn_preview_multi.setMinimumWidth(btn_min_width)
        self.btn_preview_multi.clicked.connect(self._preview_multi)
        layout.addWidget(self.btn_preview_multi)

        self.btn_render = QPushButton("◆  Render Current View")
        self.btn_render.setObjectName("RenderBtn")
        self.btn_render.setEnabled(False)
        self.btn_render.setMinimumWidth(btn_min_width)
        self.btn_render.clicked.connect(self._render_view)
        layout.addWidget(self.btn_render)

        self.btn_stop = QPushButton("■  Stop")
        self.btn_stop.setObjectName("StopBtn")
        self.btn_stop.setEnabled(False)
        self.btn_stop.setMinimumWidth(btn_min_width)
        self.btn_stop.clicked.connect(self._stop)
        layout.addWidget(self.btn_stop)

        layout.addStretch()
        return grp

    def _build_live_panel(self):
        grp = SciFiGroupBox("LIVE ADJUSTMENTS  (VMD \u6253\u5f00\u540e\u53ef\u7528)")
        layout = QGridLayout(grp)
        layout.setVerticalSpacing(6)
        layout.setHorizontalSpacing(8)

        layout.addWidget(QLabel("Isovalue:"), 0, 0)
        self.iso_slider = QSlider(Qt.Horizontal)
        self.iso_slider.setRange(5, 500)
        self.iso_slider.setValue(50)
        self.iso_slider.setEnabled(False)
        self.iso_slider.valueChanged.connect(self._on_iso_slider_changed)
        layout.addWidget(self.iso_slider, 0, 1)
        self.iso_value_label = QLabel("0.050")
        self.iso_value_label.setMinimumWidth(50)
        self.iso_value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.iso_value_label, 0, 2)

        layout.addWidget(QLabel("Opacity:"), 1, 0)
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(5, 100)
        self.opacity_slider.setValue(75)
        self.opacity_slider.setEnabled(False)
        self.opacity_slider.valueChanged.connect(self._on_opacity_slider_changed)
        layout.addWidget(self.opacity_slider, 1, 1)
        self.opacity_value_label = QLabel("0.75")
        self.opacity_value_label.setMinimumWidth(50)
        self.opacity_value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.opacity_value_label, 1, 2)

        layout.setColumnStretch(1, 1)
        return grp

    def _build_hydrogen_panel(self):
        grp = SciFiGroupBox("HIDE HYDROGEN")
        layout = QHBoxLayout(grp)
        layout.setSpacing(8)

        self.btn_h_filter = QPushButton("Hide All Hydrogens")
        self.btn_h_filter.setEnabled(False)
        self.btn_h_filter.clicked.connect(self._toggle_h_filter)
        layout.addWidget(self.btn_h_filter)

        layout.addWidget(QLabel("Keep indices (comma separated):"))
        self.var_h_indices = QLineEdit()
        self.var_h_indices.setMaximumWidth(180)
        self.var_h_indices.setPlaceholderText("empty = hide all")
        layout.addWidget(self.var_h_indices)

        layout.addStretch()
        return grp

    def _build_draw_bond_panel(self):
        grp = SciFiGroupBox("DRAW DASHED LINE")
        layout = QGridLayout(grp)
        layout.setVerticalSpacing(4)
        layout.setHorizontalSpacing(6)

        row = 0
        layout.addWidget(QLabel("Atom 1:"), row, 0)
        self.var_bond_atom1 = QLineEdit("0")
        self.var_bond_atom1.setMaximumWidth(50)
        layout.addWidget(self.var_bond_atom1, row, 1)

        layout.addWidget(QLabel("Atom 2:"), row, 2)
        self.var_bond_atom2 = QLineEdit("1")
        self.var_bond_atom2.setMaximumWidth(50)
        layout.addWidget(self.var_bond_atom2, row, 3)

        layout.addWidget(QLabel("Color:"), row, 4)
        self.var_bond_color = QComboBox()
        self.var_bond_color.addItems([
            "Gray", "Cyan", "Yellow", "Red", "Blue", "Green", "White", "Black"])
        self.var_bond_color.setCurrentIndex(0)
        self.var_bond_color.setMaximumWidth(80)
        layout.addWidget(self.var_bond_color, row, 5)

        row += 1
        layout.addWidget(QLabel("Type:"), row, 0)
        self.var_bond_type = QComboBox()
        self.var_bond_type.addItems([
            "Dots", "Dashed(pymol)", "Cylinder", "Sphere", "Arrow(cone)", "Line"])
        self.var_bond_type.setCurrentIndex(0)
        self.var_bond_type.setMaximumWidth(110)
        layout.addWidget(self.var_bond_type, row, 1)

        layout.addWidget(QLabel("Material:"), row, 2)
        self.var_bond_mat = QComboBox()
        self.var_bond_mat.addItems(["50% Transparent", "Opaque", "Transparent"])
        self.var_bond_mat.setCurrentIndex(0)
        self.var_bond_mat.setMaximumWidth(130)
        layout.addWidget(self.var_bond_mat, row, 3)

        layout.addWidget(QLabel("Segments:"), row, 4)
        self.var_bond_nbars = QLineEdit("10")
        self.var_bond_nbars.setMaximumWidth(40)
        layout.addWidget(self.var_bond_nbars, row, 5)

        row += 1
        layout.addWidget(QLabel("Spacing:"), row, 0)
        self.var_bond_space = QLineEdit("1.2")
        self.var_bond_space.setMaximumWidth(50)
        layout.addWidget(self.var_bond_space, row, 1)

        layout.addWidget(QLabel("Radius:"), row, 2)
        self.var_bond_radius = QLineEdit("0.06")
        self.var_bond_radius.setMaximumWidth(50)
        layout.addWidget(self.var_bond_radius, row, 3)

        bond_btn_frame = QHBoxLayout()
        bond_btn_frame.setSpacing(4)
        self.btn_draw_bond = QPushButton("Draw Line")
        self.btn_draw_bond.setEnabled(False)
        self.btn_draw_bond.clicked.connect(self._draw_bond)
        bond_btn_frame.addWidget(self.btn_draw_bond)

        self.btn_undo_bond = QPushButton("Undo")
        self.btn_undo_bond.setEnabled(False)
        self.btn_undo_bond.setObjectName("SmallBtn")
        self.btn_undo_bond.clicked.connect(self._undo_bond)
        bond_btn_frame.addWidget(self.btn_undo_bond)

        self.btn_clear_bond = QPushButton("Clear All")
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

    def _setup_shortcuts(self):
        pass

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_PageUp:
            self._key_iso_up()
        elif key == Qt.Key_PageDown:
            self._key_iso_down()
        elif key == Qt.Key_Home:
            self._key_opacity_up()
        elif key == Qt.Key_End:
            self._key_opacity_down()
        else:
            super().keyPressEvent(event)

    # ── Helper Methods ──

    def _make_style_icon(self, style):
        """Build a dual-color icon (pos|neg) for style combo preview."""
        VMD_BUILTIN = {
            12: (0.00, 1.00, 0.00),  # green
            22: (0.00, 0.00, 1.00),  # blue
        }
        def _rgb(color_entry):
            if color_entry[1] is not None:
                return [int(c * 255) for c in color_entry[1:4]]
            return [int(c * 255) for c in VMD_BUILTIN.get(color_entry[0], (0.5, 0.5, 0.5))]

        pos = style.get("pos_color", [31, 0.5, 0.5, 0.5])
        neg = style.get("neg_color", [32, 0.5, 0.5, 0.5])
        r1, g1, b1 = _rgb(pos)
        r2, g2, b2 = _rgb(neg)

        pm = QPixmap(30, 13)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(r1, g1, b1))
        p.drawRoundedRect(0, 0, 14, 13, 2, 2)
        p.setBrush(QColor(r2, g2, b2))
        p.drawRoundedRect(16, 0, 14, 13, 2, 2)
        p.end()
        return QIcon(pm)

    def _append_log(self, msg):
        self.log_text.moveCursor(QTextCursor.End)
        self.log_text.insertPlainText(msg + "\n")
        self.log_text.moveCursor(QTextCursor.End)

    def _set_progress(self, msg):
        self.progress_label.setText(f"◆  {msg}")

    def _get_style_name(self):
        val = self.var_style.currentText().strip()
        if val:
            return val.split("  ")[0].strip()
        return "sob-art"

    def _get_orbitals(self):
        orb_str = self.var_orbital.text().strip()
        if not orb_str:
            return []
        return [x.strip() for x in orb_str.split(',') if x.strip()]

    def _add_orbital(self, orb):
        current = self.var_orbital.text().strip()
        if not current:
            self.var_orbital.setText(orb)
        else:
            orbs = [x.strip() for x in current.split(',') if x.strip()]
            if orb not in orbs:
                orbs.append(orb)
                self.var_orbital.setText(','.join(orbs))

    def _extract_orbital_name(self, cube_path):
        basename = os.path.basename(cube_path)
        name_without_ext = os.path.splitext(basename)[0]
        if '_MO' in name_without_ext:
            return name_without_ext.rsplit('_MO', 1)[1]
        return name_without_ext

    def _get_paths(self):
        vmd = self.var_vmd.text().strip()
        tachyon = os.path.join(os.path.dirname(vmd), "tachyon_WIN32.exe")
        return {
            "multiwfn": self.var_mw.text().strip(),
            "vmd": vmd,
            "tachyon": tachyon,
        }

    def _save_paths(self):
        vmd = self.var_vmd.text().strip()
        tachyon = os.path.join(os.path.dirname(vmd), "tachyon_WIN32.exe")
        backend.save_config(self.var_mw.text().strip(), vmd, tachyon)

    def _get_params(self):
        orbitals = self._get_orbitals()
        orbital = orbitals[0] if orbitals else ""
        try:
            iso = float(self.var_iso.text().strip())
        except ValueError:
            iso = 0.05
        grid = self.var_grid.currentText().strip()
        style_name = self._get_style_name()
        try:
            res_str = self.var_res.currentText().strip()
            w, h = res_str.split("x")
            resolution = (int(w), int(h))
        except (ValueError, AttributeError):
            resolution = (2000, 1500)
        shade_id = self.shade_group.checkedId()
        shade_mode = "full" if shade_id == 0 else "medium"
        return orbital, iso, grid, style_name, resolution, shade_mode

    # ── Browse Methods ──

    def _browse_exe(self, which):
        path, _ = QFileDialog.getOpenFileName(
            self, f"Select {which.title()} Executable", "", "Executable (*.exe)")
        if path:
            if which == "multiwfn":
                self.var_mw.setText(path)
            elif which == "vmd":
                self.var_vmd.setText(path)

    def _browse_input(self):
        if self.mode_group.checkedId() == 0:
            path = QFileDialog.getExistingDirectory(self, "Select Input Folder")
        else:
            path, _ = QFileDialog.getOpenFileName(
                self, "Select Input File", "",
                "All Supported (*.fchk *.molden *.molden.input *.cube);;"
                "Formatted Checkpoint (*.fchk);;All Files (*.*)")
        if path:
            self.var_path.setText(path)

    def _browse_out(self):
        path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if path:
            self.var_out.setText(path)

    # ── Core Actions ──

    def _run_cubes(self):
        if self.running:
            return
        path = self.var_path.text().strip()
        if not path:
            QMessageBox.warning(self, "Warning", "Please select file or folder first")
            return

        exe_paths = self._get_paths()
        if not os.path.exists(exe_paths["multiwfn"]):
            QMessageBox.warning(self, "Path Error",
                f"Multiwfn not found:\n{exe_paths['multiwfn']}")
            return
        if not os.path.exists(exe_paths["vmd"]):
            QMessageBox.warning(self, "Path Error",
                f"VMD not found:\n{exe_paths['vmd']}")
            return

        self._save_paths()

        files = (sorted(glob.glob(os.path.join(path, "*.fchk")))
                 if os.path.isdir(path) else [path])
        if not files:
            QMessageBox.warning(self, "Warning", "No .fchk files found")
            return

        out = self.var_out.text().strip() or (
            path if os.path.isdir(path) else os.path.dirname(path))
        os.makedirs(out, exist_ok=True)

        orbitals = self._get_orbitals()
        if not orbitals:
            QMessageBox.warning(self, "Warning", "Please enter orbital number first")
            return

        orbital, iso, grid, style_name, resolution, shade_mode = self._get_params()
        auto_render = self.var_auto.isChecked()
        do_open = self.var_open.isChecked()

        self.running = True
        self._set_buttons_state("running")

        self.worker = CubeWorker(
            files, out, orbitals, iso, grid, style_name,
            resolution, shade_mode, auto_render, exe_paths, do_open)
        self.worker.log_signal.connect(self._append_log)
        self.worker.progress_signal.connect(self._set_progress)
        self.worker.finished_signal.connect(self._on_cubes_done)
        self.worker.start()

    def _on_cubes_done(self, auto_render, ok, total, cubes):
        self.running = False
        self._set_buttons_state("idle")

        if not auto_render and cubes:
            self._current_cubes = cubes
            self._append_log(
                "\nAfter adjusting view in VMD, click [Preview (Single)] "
                "/ [Preview (Multi)] or [Render Current View]")
            self.btn_preview.setEnabled(True)
            self.btn_preview_multi.setEnabled(True)

        if auto_render:
            self._append_log(f"\nAll completed {ok}/{total}")
            self._set_progress(f"Completed: {ok}/{total}")
            if self.var_open.isChecked() and ok > 0 and cubes:
                out = self.var_out.text().strip() or os.path.dirname(self.var_path.text().strip())
                os.startfile(out)

    def _preview_single(self):
        path = self.var_path.text().strip()
        out = self.var_out.text().strip() or (
            path if os.path.isdir(path) else os.path.dirname(path))

        cubes = sorted(glob.glob(os.path.join(out, "*.cub")))
        if not cubes:
            QMessageBox.warning(self, "Warning",
                "No cube files found in output directory\nPlease click [Generate Cube] first")
            return

        from PyQt5.QtWidgets import QInputDialog
        cube_names = [os.path.basename(c) for c in cubes]
        item, ok = QInputDialog.getItem(
            self, "Select Cube File", "Choose cube file to preview:",
            cube_names, 0, False)
        if not ok or not item:
            return

        cube_path = cubes[cube_names.index(item)]
        self._do_preview(cube_path)

    def _do_preview(self, cube_path):
        self._close_persist_sock()
        try:
            iso = float(self.var_iso.text().strip())
        except ValueError:
            iso = 0.05

        style_name = self._get_style_name()
        _, _, _, _, _, shade_mode = self._get_params()
        exe_paths = self._get_paths()

        self.current_iso = iso
        self.current_opacity = None

        self._append_log(f"\nStarting VMD preview: {os.path.basename(cube_path)}")
        self._append_log(f"Style: {style_name}, Isovalue: {iso}")
        self._append_log("Adjust view in VMD, then click [Render Current View]")

        try:
            port, render_dir = backend.preview_cube(
                cube_path, isovalue=iso, style_name=style_name,
                vmd_exe=exe_paths["vmd"], shade_mode=shade_mode)
            if port:
                self.vmd_port = port
                self.vmd_render_dir = render_dir
                self.vmd_cube_path = cube_path
                self.vmd_multi_cubes = None
                self.btn_render.setEnabled(True)
                self.btn_draw_bond.setEnabled(True)
                self.btn_undo_bond.setEnabled(True)
                self.btn_clear_bond.setEnabled(True)
                self.btn_h_filter.setEnabled(True)
                self.iso_slider.setEnabled(True)
                self.iso_slider.blockSignals(True)
                self.iso_slider.setValue(int(iso * 1000))
                self.iso_slider.blockSignals(False)
                self.iso_value_label.setText(f"{iso:.3f}")
                self.opacity_slider.setEnabled(True)
                if self.current_opacity is None:
                    style = backend.STYLES.get(style_name, backend.STYLES["sob-art"])
                    self.current_opacity = style["surface_mat"][5]
                self.opacity_slider.blockSignals(True)
                self.opacity_slider.setValue(int(self.current_opacity * 100))
                self.opacity_slider.blockSignals(False)
                self.opacity_value_label.setText(f"{self.current_opacity:.2f}")
                self._append_log(f"VMD started (port {port}), waiting for operations...")
            else:
                self._append_log("VMD start failed")
        except Exception as e:
            self._append_log(f"VMD start error: {e}")

    def _preview_multi(self):
        path = self.var_path.text().strip()
        out = self.var_out.text().strip() or (
            path if os.path.isdir(path) else os.path.dirname(path))

        all_cubes = sorted(glob.glob(os.path.join(out, "*_MO*.cub")))
        if not all_cubes:
            QMessageBox.warning(self, "Warning",
                "No orbital cube files found in output directory\n"
                "Please click [Generate Cube] first")
            return

        from PyQt5.QtWidgets import QDialog, QListWidget, QDialogButtonBox

        if len(all_cubes) == 1:
            cube_path = all_cubes[0]
            cubes = [(cube_path, self._extract_orbital_name(cube_path))]
        else:
            dlg = QDialog(self)
            dlg.setWindowTitle("Select orbitals to preview")
            dlg.resize(500, 420)
            dlg_layout = QVBoxLayout(dlg)

            dlg_layout.addWidget(QLabel(
                "Select orbitals to preview (multi-select with Ctrl or Shift):"))

            list_widget = QListWidget()
            list_widget.setSelectionMode(QListWidget.ExtendedSelection)
            for i, c in enumerate(all_cubes):
                list_widget.addItem(os.path.basename(c))
                list_widget.item(i).setSelected(True)
            dlg_layout.addWidget(list_widget)

            btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            btn_box.accepted.connect(dlg.accept)
            btn_box.rejected.connect(dlg.reject)
            dlg_layout.addWidget(btn_box)

            if dlg.exec_() != QDialog.Accepted:
                return

            selected = [all_cubes[i.row()] for i in list_widget.selectedIndexes()]
            if not selected:
                return
            cubes = [(c, self._extract_orbital_name(c)) for c in selected]

        self._do_preview_multi(cubes)

    def _do_preview_multi(self, cubes):
        self._close_persist_sock()
        orbitals = [orb for _, orb in cubes]
        try:
            iso = float(self.var_iso.text().strip())
        except ValueError:
            iso = 0.05

        style_name = self._get_style_name()
        _, _, _, _, _, shade_mode = self._get_params()
        exe_paths = self._get_paths()

        h_str = self.var_h_indices.text().strip()
        if h_str:
            try:
                keep_h_indices = [int(x.strip()) for x in h_str.split(",") if x.strip()]
            except ValueError:
                keep_h_indices = []
        else:
            keep_h_indices = None

        self.current_iso = iso
        self.current_opacity = None

        orb_names = ", ".join([orb for _, orb in cubes])
        self._append_log(f"\nStarting VMD multi-orbital preview: {orb_names}")
        self._append_log(f"Style: {style_name}, Isovalue: {iso}")
        self._append_log("Adjust view in VMD, then click [Render Current View]")

        try:
            port, render_dir, copied_cubes = backend.preview_multi_cubes(
                cubes, iso, style_name=style_name,
                vmd_exe=exe_paths["vmd"], shade_mode=shade_mode,
                keep_h_indices=keep_h_indices)
            if port:
                self.vmd_port = port
                self.vmd_render_dir = render_dir
                self.vmd_multi_cubes = copied_cubes
                self.vmd_cube_path = None
                self.btn_render.setEnabled(True)
                self.btn_draw_bond.setEnabled(True)
                self.btn_undo_bond.setEnabled(True)
                self.btn_clear_bond.setEnabled(True)
                self.btn_h_filter.setEnabled(True)
                self.iso_slider.setEnabled(True)
                self.iso_slider.blockSignals(True)
                self.iso_slider.setValue(int(iso * 1000))
                self.iso_slider.blockSignals(False)
                self.iso_value_label.setText(f"{iso:.3f}")
                self.opacity_slider.setEnabled(True)
                if self.current_opacity is None:
                    style = backend.STYLES.get(style_name, backend.STYLES["sob-art"])
                    self.current_opacity = style["surface_mat"][5]
                self.opacity_slider.blockSignals(True)
                self.opacity_slider.setValue(int(self.current_opacity * 100))
                self.opacity_slider.blockSignals(False)
                self.opacity_value_label.setText(f"{self.current_opacity:.2f}")
                self._append_log(f"VMD started (port {port}), waiting for operations...")
            else:
                self._append_log("VMD start failed")
        except Exception as e:
            self._append_log(f"VMD start error: {e}")

    def _render_view(self):
        if not self.vmd_port or not self.vmd_render_dir:
            QMessageBox.warning(self, "Warning",
                "Please click [Preview] to open VMD first")
            return

        out = self.var_out.text().strip()
        if out and not os.path.isdir(out):
            os.makedirs(out, exist_ok=True)

        _, _, _, style_name, resolution, shade_mode = self._get_params()
        exe_paths = self._get_paths()

        output_png = None
        if self.vmd_cube_path:
            cube_stem = os.path.splitext(os.path.basename(self.vmd_cube_path))[0]
            fchk_name = cube_stem.rsplit("_MO", 1)[0]
            orbital = self._get_orbitals()
            orbital_str = ",".join(orbital) if orbital else "unknown"
            output_png = os.path.join(out, f"{fchk_name}_MO{orbital_str}.png") if out else None
        elif self.vmd_multi_cubes and self.vmd_multi_cubes[0][0]:
            cube_stem = os.path.splitext(os.path.basename(self.vmd_multi_cubes[0][0]))[0]
            fchk_name = cube_stem.rsplit("_MO", 1)[0]
            orbitals = self._get_orbitals()
            orbital_suffix = "_".join(orbitals) if orbitals else "multi"
            output_png = os.path.join(out, f"{fchk_name}_MO{orbital_suffix}.png") if out else None

        trans_raster = self.var_trans_raster.isChecked()
        threads = int(self.var_threads.currentText())

        self.btn_render.setEnabled(False)
        self.render_worker = RenderWorker(
            self.vmd_port, self.vmd_render_dir, output_png,
            exe_paths["tachyon"], resolution, style_name,
            shade_mode, trans_raster, threads)
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

    # ── Hydrogen Filter ──

    def _toggle_h_filter(self):
        if not self.vmd_port:
            self._append_log("Please click preview button to start VMD first")
            return

        current_text = self.btn_h_filter.text()
        if current_text == "Hide All Hydrogens":
            self.btn_h_filter.setText("Show All Hydrogens")
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
                f'foreach mid [molinfo list] {{'
                f'  mol modselect 0 $mid "{sel_str}"'
                f'}}'
            )
            self._send_vmd_cmd(cmd)
            self._append_log("[Hide H] Hid hydrogens for all molecules")
        else:
            self.btn_h_filter.setText("Hide All Hydrogens")
            cmd = 'foreach mid [molinfo list] { mol modselect 0 $mid all }'
            self._send_vmd_cmd(cmd)
            self._append_log("[Hide H] Restored hydrogens for all molecules")

    # ── Draw Bond Methods ──

    def _draw_bond(self):
        if not self.vmd_port:
            QMessageBox.warning(self, "Warning",
                "Please click [Preview] to open VMD first")
            return
        a1 = self.var_bond_atom1.text().strip()
        a2 = self.var_bond_atom2.text().strip()
        if not a1 or not a2:
            QMessageBox.warning(self, "Warning", "Please enter two atom indices")
            return

        bond_color_map = {
            "Black": "black", "Gray": "gray", "Cyan": "cyan", "Yellow": "yellow",
            "Red": "red", "Blue": "blue", "Green": "green", "White": "white"}
        bond_type_map = {
            "Dots": "dots", "Dashed(pymol)": "pymol",
            "Cylinder": "cylinder", "Sphere": "sphere",
            "Arrow(cone)": "cone", "Line": "line"}
        bond_mat_map = {
            "Opaque": "Opaque", "50% Transparent": "HalfTransparent",
            "Transparent": "Transparent"}

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
            self._append_log(f"[Draw Bond] Atom{a1}-{a2} {color} {btype} {mat}")
            self.btn_undo_bond.setEnabled(True)
        else:
            self._append_log("[Draw Bond] Failed")

    def _undo_bond(self):
        resp = self._send_vmd_cmd("draw_bond_undo")
        if resp and "ERROR" not in resp:
            self._append_log("[Bond] Undo")
        else:
            self._append_log("[Bond] Undo failed")

    def _clear_bond(self):
        resp = self._send_vmd_cmd("draw_bond_clear")
        if resp and "ERROR" not in resp:
            self._append_log("[Bond] Cleared all")
        else:
            self._append_log("[Bond] Clear failed")

    # ── Socket Communication ──

    def _send_vmd_cmd(self, cmd):
        if not self.vmd_port:
            return None
        try:
            sock = getattr(self, '_vmd_persist_sock', None)
            if sock is None:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect(("127.0.0.1", self.vmd_port))
                self._vmd_persist_sock = sock
            sock.sendall((cmd + "\n").encode("utf-8"))
            resp = b""
            try:
                sock.settimeout(0.5)
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    resp += chunk
                    if b"\n" in resp:
                        break
            except socket.timeout:
                pass
            sock.settimeout(5)
            return resp.decode("utf-8", errors="replace").strip()
        except Exception:
            self._close_persist_sock()
            return None

    def _close_persist_sock(self):
        sock = getattr(self, '_vmd_persist_sock', None)
        if sock:
            try:
                sock.close()
            except Exception:
                pass
            self._vmd_persist_sock = None

    # ── Keyboard Shortcuts ──

    def _key_iso_up(self):
        self.current_iso = round(min(self.current_iso + self.iso_step, 0.5), 4)
        self._apply_iso_change()

    def _key_iso_down(self):
        self.current_iso = round(max(self.current_iso - self.iso_step, 0.005), 4)
        self._apply_iso_change()

    def _key_opacity_up(self):
        if self.current_opacity is None:
            style = backend.STYLES.get(self._get_style_name(), backend.STYLES["sob-art"])
            self.current_opacity = style["surface_mat"][5]
        self.current_opacity = round(min(self.current_opacity + self.opacity_step, 1.0), 2)
        self._apply_opacity_change()

    def _key_opacity_down(self):
        if self.current_opacity is None:
            style = backend.STYLES.get(self._get_style_name(), backend.STYLES["sob-art"])
            self.current_opacity = style["surface_mat"][5]
        self.current_opacity = round(max(self.current_opacity - self.opacity_step, 0.05), 2)
        self._apply_opacity_change()

    # ── Slider Handlers ──

    def _on_iso_slider_changed(self, val):
        if not self.vmd_port:
            return
        iso = val / 1000.0
        self.current_iso = iso
        self.iso_value_label.setText(f"{iso:.3f}")
        self.var_iso.blockSignals(True)
        self.var_iso.setText(f"{iso:.4g}")
        self.var_iso.blockSignals(False)
        cmd = f"mol modstyle 1 top Isosurface {iso} 0 0 0 1 1"
        self._send_vmd_cmd(cmd)
        cmd = f"mol modstyle 2 top Isosurface -{iso} 0 0 0 1 1"
        self._send_vmd_cmd(cmd)

    def _on_opacity_slider_changed(self, val):
        if not self.vmd_port:
            return
        op = val / 100.0
        self.current_opacity = op
        self.opacity_value_label.setText(f"{op:.2f}")
        for mat_name in ["_stl_a", "_stl_b"]:
            cmd = f"material change opacity {mat_name} {op}"
            self._send_vmd_cmd(cmd)

    def _apply_iso_change(self):
        iso = self.current_iso
        self.var_iso.setText(f"{iso:.4g}")
        self.iso_slider.blockSignals(True)
        self.iso_slider.setValue(int(iso * 1000))
        self.iso_slider.blockSignals(False)
        self.iso_value_label.setText(f"{iso:.3f}")
        cmd = f"mol modstyle 1 top Isosurface {iso} 0 0 0 1 1"
        resp1 = self._send_vmd_cmd(cmd)
        cmd = f"mol modstyle 2 top Isosurface -{iso} 0 0 0 1 1"
        resp2 = self._send_vmd_cmd(cmd)
        status = "OK" if resp1 and "ERROR" not in (resp1 + (resp2 or "")) else "VMD not connected"
        self._append_log(f"[Isosurface] iso = {iso:.4g}  ({status})")

    def _apply_opacity_change(self):
        op = self.current_opacity
        self.opacity_slider.blockSignals(True)
        self.opacity_slider.setValue(int(op * 100))
        self.opacity_slider.blockSignals(False)
        self.opacity_value_label.setText(f"{op:.2f}")
        for mat_name in ["_stl_a", "_stl_b"]:
            cmd = f"material change opacity {mat_name} {op}"
            self._send_vmd_cmd(cmd)
        self._append_log(f"[Opacity] opacity = {op:.2f}")

    # ── Button State Management ──

    def _set_buttons_state(self, state):
        if state == "running":
            self.btn_run.setEnabled(False)
            self.btn_preview.setEnabled(False)
            self.btn_preview_multi.setEnabled(False)
            self.btn_render.setEnabled(False)
            self.btn_stop.setEnabled(True)
            self.btn_h_filter.setEnabled(False)
            self.btn_draw_bond.setEnabled(False)
            self.btn_undo_bond.setEnabled(False)
            self.btn_clear_bond.setEnabled(False)
            self.iso_slider.setEnabled(False)
            self.opacity_slider.setEnabled(False)
        else:
            self.btn_run.setEnabled(True)
            self.btn_stop.setEnabled(False)


# ── Entry Point ───────────────────────────────────────────
def main():
    if len(sys.argv) > 1:
        import argparse
        p = argparse.ArgumentParser(
            description="Multiwfn + VMD/Tachyon Orbital Isosurface Visualization v5.1")
        p.add_argument("input", help="fchk file or folder")
        p.add_argument("--mo", default="h", help="Orbital (h/l/h-1/number)")
        p.add_argument("--iso", type=float, default=0.05, help="Isosurface threshold")
        p.add_argument("--grid", default="2", help="Grid quality (1/2/3)")
        p.add_argument("--style", default="sob_Gold",
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
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        window = OrbitalVisApp()
        window.show()
        sys.exit(app.exec_())


if __name__ == "__main__":
    main()
