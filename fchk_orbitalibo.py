#!/usr/bin/env python3
"""
IGMH 等值面可视化工具 v1 (基于 fchk_orbitalibo.py 框架)
VMD (预览) + Tachyon (渲染)

功能：
  - 选择 dg_inter.cub 和 sl2r.cub 两个 cube 文件
  - VMD GUI 预览，实时调整等值面
  - 一键 Tachyon 高质量渲染
  - 11 种渲染样式（vcube2.0）
  - PageUp/PageDown 调等值面, Home/End 调透明度
  - 画虚线功能标注氢键等相互作用
  - 氢原子过滤功能

用法：
  直接运行 -> 弹出 GUI
"""

import os
import sys
import subprocess
import threading
import shutil
import time
import tempfile
import socket


# ── 默认路径 ──────────────────────────────────────────────
DEFAULT_VMD = r"C:\Program Files (x86)\University of Illinois\VMD\vmd.exe"
DEFAULT_TACHYON = r"C:\Program Files (x86)\University of Illinois\VMD\tachyon_WIN32.exe"

CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(sys.argv[0] if getattr(sys, 'frozen', False) else __file__)),
    "igmh.ini"
)


def load_config():
    import configparser
    cfg = configparser.ConfigParser()
    paths = {"vmd": DEFAULT_VMD, "tachyon": DEFAULT_TACHYON}
    if os.path.exists(CONFIG_FILE):
        cfg.read(CONFIG_FILE, encoding="utf-8")
        if "paths" in cfg:
            for k in paths:
                if k in cfg["paths"] and cfg["paths"][k]:
                    paths[k] = cfg["paths"][k]
    return paths


def save_config(vmd, tachyon):
    import configparser
    cfg = configparser.ConfigParser()
    cfg["paths"] = {"vmd": vmd, "tachyon": tachyon}
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        cfg.write(f)


# ── 原子元素着色（GaussView 配色，Python 字典）─────────────
GVIEW_COLORS = {
    "H":  (101, 0.8000, 0.8000, 0.8000),
    "He": (102, 0.8471, 1.0000, 1.0000),
    "Li": (103, 0.8000, 0.4863, 1.0000),
    "Be": (104, 0.8000, 1.0000, 0.0000),
    "B":  (105, 1.0000, 0.7098, 0.7098),
    "C":  (106, 0.5569, 0.5569, 0.5569),
    "N":  (107, 0.0980, 0.0980, 0.8980),
    "O":  (108, 0.8980, 0.0000, 0.0000),
    "F":  (109, 0.6980, 1.0000, 1.0000),
    "Ne": (110, 0.6863, 0.8863, 0.9569),
    "Na": (111, 0.6667, 0.3569, 0.9490),
    "Mg": (112, 0.6980, 0.8000, 0.0000),
    "Al": (113, 0.8196, 0.6471, 0.6471),
    "Si": (114, 0.4980, 0.6000, 0.6000),
    "P":  (115, 1.0000, 0.4980, 0.0000),
    "S":  (116, 1.0000, 0.7765, 0.1569),
    "Cl": (117, 0.0980, 0.9373, 0.0980),
    "Ar": (118, 0.4980, 0.8196, 0.8863),
    "K":  (119, 0.5569, 0.2471, 0.8275),
    "Ca": (120, 0.6000, 0.6000, 0.0000),
    "Sc": (121, 0.8980, 0.8980, 0.8863),
    "Ti": (122, 0.7490, 0.7569, 0.7765),
    "V":  (123, 0.6471, 0.6471, 0.6667),
    "Cr": (124, 0.5373, 0.6000, 0.7765),
    "Mn": (125, 0.6078, 0.4784, 0.7765),
    "Fe": (126, 0.4980, 0.4784, 0.7765),
    "Co": (127, 0.3569, 0.4275, 1.0000),
    "Ni": (128, 0.3569, 0.4784, 0.7569),
    "Cu": (129, 1.0000, 0.4784, 0.3765),
    "Zn": (130, 0.4863, 0.4980, 0.6863),
    "Ga": (131, 0.7569, 0.5569, 0.5569),
    "Ge": (132, 0.4000, 0.5569, 0.5569),
    "As": (133, 0.7373, 0.4980, 0.8863),
    "Se": (134, 1.0000, 0.6275, 0.0000),
    "Br": (135, 0.6471, 0.1294, 0.1294),
    "Kr": (136, 0.3569, 0.7294, 0.8196),
    "Rb": (137, 0.4392, 0.1765, 0.6863),
    "Sr": (138, 0.4980, 0.4000, 0.0000),
    "Y":  (139, 0.5765, 0.9882, 1.0000),
    "Zr": (140, 0.5765, 0.8784, 0.8784),
    "Nb": (141, 0.4471, 0.7569, 0.7882),
    "Mo": (142, 0.3294, 0.7098, 0.7098),
    "Tc": (143, 0.2275, 0.6196, 0.6588),
    "Ru": (144, 0.1373, 0.5569, 0.5882),
    "Rh": (145, 0.0392, 0.4863, 0.5490),
    "Pd": (146, 0.0000, 0.4078, 0.5176),
    "Ag": (147, 0.6000, 0.7765, 1.0000),
    "Cd": (148, 1.0000, 0.8471, 0.5569),
    "In": (149, 0.6471, 0.4588, 0.4471),
    "Sn": (150, 0.4000, 0.4980, 0.4980),
    "Sb": (151, 0.6196, 0.3882, 0.7098),
    "Te": (152, 0.8275, 0.4784, 0.0000),
    "I":  (153, 0.5765, 0.0000, 0.5765),
    "Xe": (154, 0.2588, 0.6196, 0.6863),
    "Cs": (155, 0.3373, 0.0863, 0.5569),
    "Ba": (156, 0.4000, 0.2000, 0.0000),
    "La": (157, 0.4392, 0.8667, 1.0000),
    "Ce": (158, 1.0000, 1.0000, 0.7765),
    "Pr": (159, 0.8471, 1.0000, 0.7765),
    "Nd": (160, 0.7765, 1.0000, 0.7765),
    "Pm": (161, 0.6392, 1.0000, 0.7765),
    "Sm": (162, 0.5569, 1.0000, 0.7765),
    "Eu": (163, 0.3765, 1.0000, 0.7765),
    "Gd": (164, 0.2667, 1.0000, 0.7765),
    "Tb": (165, 0.1882, 1.0000, 0.7765),
    "Dy": (166, 0.1176, 1.0000, 0.7098),
    "Ho": (167, 0.0000, 1.0000, 0.7098),
    "Er": (168, 0.0000, 0.8980, 0.4588),
    "Tm": (169, 0.0000, 0.8275, 0.3176),
    "Yb": (170, 0.0000, 0.7490, 0.2196),
    "Lu": (171, 0.0000, 0.6667, 0.1373),
    "Hf": (172, 0.2980, 0.7569, 1.0000),
    "Ta": (173, 0.2980, 0.6471, 1.0000),
    "W":  (174, 0.1490, 0.5765, 0.8392),
    "Re": (175, 0.1490, 0.4863, 0.6667),
    "Os": (176, 0.1490, 0.4000, 0.5882),
    "Ir": (177, 0.0863, 0.3294, 0.5294),
    "Pt": (178, 0.0863, 0.3569, 0.5569),
    "Au": (179, 1.0000, 0.8196, 0.1373),
    "Hg": (180, 0.7098, 0.7098, 0.7569),
    "Tl": (181, 0.6471, 0.3294, 0.2980),
    "Pb": (182, 0.3373, 0.3490, 0.3765),
    "Bi": (183, 0.6196, 0.3098, 0.7098),
    "Po": (184, 0.6667, 0.3569, 0.0000),
    "At": (185, 0.4588, 0.3098, 0.2667),
    "Rn": (186, 0.2588, 0.5098, 0.5882),
    "Fr": (187, 0.2588, 0.0000, 0.4000),
    "Ra": (188, 0.2980, 0.0980, 0.0000),
    "Ac": (189, 0.4392, 0.6667, 0.9765),
    "Th": (190, 0.0000, 0.7294, 1.0000),
    "Pa": (191, 0.0000, 0.6275, 1.0000),
    "U":  (192, 0.0000, 0.5569, 1.0000),
    "Np": (193, 0.0000, 0.4980, 0.9490),
    "Pu": (194, 0.0000, 0.4196, 0.9490),
    "Am": (195, 0.3294, 0.3569, 0.9490),
    "Cm": (196, 0.4667, 0.3569, 0.8863),
    "Bk": (197, 0.5373, 0.3686, 0.8863),
    "Cf": (198, 0.6275, 0.2078, 0.8275),
    "Es": (199, 0.6588, 0.1686, 0.7765),
    "Fm": (200, 0.6980, 0.1176, 0.7294),
    "Md": (201, 0.6980, 0.0471, 0.6471),
    "No": (202, 0.7373, 0.0471, 0.5294),
    "Lr": (203, 0.7765, 0.0000, 0.4000),
    "Rf": (204, 1.0000, 0.4980, 0.4980),
    "Db": (205, 0.8980, 0.4000, 0.4000),
    "Sg": (206, 0.8000, 0.2980, 0.2980),
    "Bh": (207, 0.6980, 0.2000, 0.2000),
    "Hs": (208, 0.6000, 0.0980, 0.0980),
    "Mt": (209, 0.5490, 0.0000, 0.0000),
    "Ds": (210, 0.4980, 0.0000, 0.0000),
    "Rg": (211, 0.4471, 0.0000, 0.0000),
}


def _gview_color_tcl(exclude=None):
    lines = []
    for elem, (cid, r, g, b) in GVIEW_COLORS.items():
        if exclude and elem in exclude:
            continue
        lines.append(f"color change rgb {cid} {r:.4f} {g:.4f} {b:.4f}")
    for elem, (cid, r, g, b) in GVIEW_COLORS.items():
        if exclude and elem in exclude:
            continue
        lines.append(f"color Element {elem} {cid}")
    return "\n".join(lines)


# ── vcube2.0 样式定义 ────────────────────────────────────
STYLES = {
    "sob-art": {
        "desc": "绿蓝, 高光, 经典 (sobereva推荐)",
        "tachyon_options": "-trans_raster3d",
        "lights": {"0": "on", "1": "on", "2": "off", "3": "on"},
        "shadows": "off", "ao": "off",
        "surface_mat": [0.1, 0.6, 1.0, 1.0, 0.0, 0.75, 0.0, 0.0, 1.0],
        "surface_mat_b": [0.1, 0.6, 1.0, 1.0, 0.0, 0.75, 0.0, 0.0, 1.0],
        "pos_color": [12, None, None],
        "neg_color": [22, None, None],
        "atom_cpk": "0.600000 0.400000 30.000000 30.000000",
        "atom_mat": [0.0, 0.65, 0.5, 0.53, 0.15, 1.0, 2.0, 0.3, 0.0],
        "c_color": "tan", "c_rgb": "0.700000 0.560000 0.360000",
    },
    "ao-shiny": {
        "desc": "橙青, 珠宝感, AO(慢)",
        "tachyon_options": "-trans_raster3d",
        "lights": {"0": "on", "1": "on", "2": "on", "3": "off"},
        "shadows": "on", "ao": "on",
        "surface_mat": [0.20, 0.8, 0.7, 0.3, 0.0, 0.7, 0.0, 0.0, 1.0],
        "surface_mat_b": [0.20, 0.8, 0.7, 0.3, 0.0, 0.7, 0.0, 0.0, 1.0],
        "pos_color": [31, 0.900, 0.500, 0.200],
        "neg_color": [32, 0.000, 0.600, 0.800],
        "atom_cpk": "0.700000 0.3500000 30.000000 30.000000",
        "atom_mat": [0.0, 0.85, 0.0, 0.53, 0.0, 1.0, 0.5, 0.9, 0.0],
        "c_color": "gray", "c_rgb": "0.600000 0.600000 0.600000",
    },
    "ao-chalky": {
        "desc": "蓝绿, 粉笔感, AO(慢)",
        "tachyon_options": "-trans_raster3d",
        "lights": {"0": "on", "1": "on", "2": "off", "3": "off"},
        "shadows": "on", "ao": "on",
        "surface_mat": [0.1, 0.85, 0.2, 0.55, 0.0, 0.8, 0.5, 0.7, 1.0],
        "surface_mat_b": [0.1, 0.85, 0.2, 0.55, 0.0, 0.8, 0.5, 0.7, 1.0],
        "pos_color": [31, 0.600, 0.900, 0.500],
        "neg_color": [32, 0.000, 0.700, 0.900],
        "atom_cpk": "0.600000 0.400000 30.000000 30.000000",
        "atom_mat": [0.0, 0.85, 0.0, 0.53, 0.0, 1.0, 0.5, 0.9, 0.0],
        "c_color": "gray", "c_rgb": "0.600000 0.600000 0.600000",
    },
    "white-green": {
        "desc": "白绿, 塑料, 半透明",
        "tachyon_options": "-trans_raster3d",
        "lights": {"0": "on", "1": "on", "2": "off", "3": "off"},
        "shadows": "off", "ao": "off",
        "surface_mat": [0.2, 0.5, 0.6, 0.85, 0.0, 0.7, 0.6, 0.6, 1.0],
        "surface_mat_b": [0.2, 0.5, 0.6, 0.85, 0.0, 0.7, 0.6, 0.6, 1.0],
        "pos_color": [31, 0.950, 0.950, 0.950],
        "neg_color": [32, 0.500, 0.900, 0.100],
        "atom_cpk": "0.600000 0.400000 30.000000 30.000000",
        "atom_mat": [0.1, 0.5, 0.1, 0.3, 0.0, 1.0, 0.5, 0.9, 0.0],
        "c_color": "gray", "c_rgb": "0.600000 0.600000 0.600000",
    },
    "white-red": {
        "desc": "白红, 柔和粉笔, 半透明",
        "tachyon_options": "-trans_raster3d",
        "lights": {"0": "on", "1": "on", "2": "off", "3": "off"},
        "shadows": "off", "ao": "off",
        "surface_mat": [0.2, 0.45, 0.05, 0.2, 0.0, 0.7, 0.0, 0.0, 1.0],
        "surface_mat_b": [0.2, 0.4, 0.2, 0.2, 0.0, 0.7, 0.3, 0.5, 1.0],
        "pos_color": [31, 0.950, 0.950, 0.950],
        "neg_color": [32, 1.000, 0.440, 0.260],
        "atom_cpk": "0.700000 0.350000 30.000000 30.000000",
        "atom_mat": [0.1, 0.5, 0.1, 0.3, 0.0, 1.0, 0.5, 0.9, 0.0],
        "c_color": "gray", "c_rgb": "0.600000 0.600000 0.600000",
    },
    "morandi-blue": {
        "desc": "莫兰迪蓝白, 磨砂玻璃",
        "tachyon_options": "-trans_raster3d",
        "lights": {"0": "on", "1": "on", "2": "on", "3": "on"},
        "shadows": "off", "ao": "off",
        "surface_mat": [0.5, 0.4, 0.0, 0.0, 0.0, 0.7, 0.3, 0.3, 1.0],
        "surface_mat_b": [0.5, 0.4, 0.0, 0.0, 0.0, 0.7, 0.3, 0.3, 1.0],
        "pos_color": [31, 0.760, 0.720, 0.650],
        "neg_color": [32, 0.470, 0.490, 0.520],
        "atom_cpk": "0.700000 0.350000 30.000000 30.000000",
        "atom_mat": [0.1, 0.5, 0.1, 0.3, 0.0, 1.0, 0.5, 0.9, 0.0],
        "c_color": "gray", "c_rgb": "0.600000 0.600000 0.600000",
    },
    "morandi-green": {
        "desc": "莫兰迪绿白, 磨砂玻璃, 不透明",
        "tachyon_options": "-trans_raster3d -shadow_filter_off",
        "lights": {"0": "on", "1": "on", "2": "off", "3": "on"},
        "shadows": "off", "ao": "off",
        "surface_mat": [0.6, 0.3, 0.1, 0.2, 0.0, 1.0, 0.4, 0.6, 1.0],
        "surface_mat_b": [0.6, 0.3, 0.1, 0.2, 0.0, 1.0, 0.4, 0.6, 1.0],
        "pos_color": [31, 0.450, 0.600, 0.400],
        "neg_color": [32, 0.850, 0.800, 0.750],
        "atom_cpk": "0.600000 0.400000 30.000000 30.000000",
        "atom_mat": [0.1, 0.5, 0.1, 0.3, 0.0, 1.0, 0.5, 0.9, 0.0],
        "c_color": "gray", "c_rgb": "0.600000 0.600000 0.600000",
    },
    "morandi-orange": {
        "desc": "莫兰迪橙蓝, 磨砂玻璃",
        "tachyon_options": "-trans_raster3d",
        "lights": {"0": "on", "1": "on", "2": "on", "3": "on"},
        "shadows": "off", "ao": "off",
        "surface_mat": [0.5, 0.4, 0.0, 0.0, 0.0, 0.7, 0.3, 0.5, 1.0],
        "surface_mat_b": [0.5, 0.4, 0.0, 0.0, 0.0, 0.7, 0.3, 0.5, 1.0],
        "pos_color": [31, 0.760, 0.570, 0.380],
        "neg_color": [32, 0.690, 0.840, 0.890],
        "atom_cpk": "0.700000 0.350000 30.000000 30.000000",
        "atom_mat": [0.1, 0.5, 0.1, 0.3, 0.0, 1.0, 0.5, 0.9, 0.0],
        "c_color": "gray", "c_rgb": "0.600000 0.600000 0.600000",
    },
    "morandi-red": {
        "desc": "莫兰迪红白, 磨砂玻璃",
        "tachyon_options": "-trans_raster3d",
        "lights": {"0": "on", "1": "on", "2": "on", "3": "on"},
        "shadows": "off", "ao": "off",
        "surface_mat": [0.5, 0.4, 0.0, 0.0, 0.0, 0.7, 0.3, 0.5, 1.0],
        "surface_mat_b": [0.5, 0.4, 0.0, 0.0, 0.0, 0.7, 0.3, 0.5, 1.0],
        "pos_color": [31, 0.660, 0.410, 0.350],
        "neg_color": [32, 0.820, 0.750, 0.650],
        "atom_cpk": "0.700000 0.350000 30.000000 30.000000",
        "atom_mat": [0.1, 0.5, 0.1, 0.3, 0.0, 1.0, 0.5, 0.9, 0.0],
        "c_color": "gray", "c_rgb": "0.600000 0.600000 0.600000",
    },
    "vmwfn0": {
        "desc": "白冰蓝, 光滑, 半透明",
        "tachyon_options": "-fullshade",
        "lights": {"0": "on", "1": "on", "2": "on", "3": "on"},
        "shadows": "off", "ao": "off",
        "surface_mat": [0.6, 0.3, 1.0, 0.95, 0.0, 0.7, 0.3, 0.3, 1.0],
        "surface_mat_b": [0.6, 0.2, 1.0, 1.0, 0.0, 0.7, 0.3, 0.3, 1.0],
        "pos_color": [31, 0.400, 0.450, 0.550],
        "neg_color": [32, 0.850, 0.820, 0.750],
        "atom_cpk": "0.700000 0.350000 30.000000 30.000000",
        "atom_mat": [0.1, 0.5, 0.1, 0.3, 0.0, 1.0, 0.5, 0.9, 0.0],
        "c_color": "gray", "c_rgb": "0.600000 0.600000 0.600000",
    },
    "vmwfn1": {
        "desc": "红白, 光滑漆面, 不透明",
        "tachyon_options": "-trans_raster3d -shadow_filter_off",
        "lights": {"0": "on", "1": "on", "2": "off", "3": "off"},
        "shadows": "off", "ao": "off",
        "surface_mat": [0.4, 0.6, 1.0, 0.9, 0.0, 1.0, 0.4, 0.6, 1.0],
        "surface_mat_b": [0.4, 0.6, 1.0, 0.9, 0.0, 1.0, 0.4, 0.6, 1.0],
        "pos_color": [31, 0.850, 0.850, 0.750],
        "neg_color": [32, 0.600, 0.200, 0.300],
        "atom_cpk": "0.600000 0.400000 30.000000 30.000000",
        "atom_mat": [0.1, 0.5, 0.1, 0.3, 0.0, 1.0, 0.5, 0.9, 0.0],
        "c_color": "gray", "c_rgb": "0.600000 0.600000 0.600000",
    },
}


def _draw_bond_tcl():
    return r"""
# === draw_bond 虚线绘制 ===
set _vmd_bond_history {}

if {[lsearch [material list] "HalfTransparent"] == -1} {
    material add HalfTransparent
    material change opacity HalfTransparent 0.5
    material change ambient HalfTransparent 0.15
    material change specular HalfTransparent 0.5
    material change shininess HalfTransparent 0.5
    material change diffuse HalfTransparent 0.85
}

proc draw_bond {args} {
    global _vmd_bond_history
    set mol1 "top"
    set index1 ""
    set mol2 "top"
    set index2 ""
    set color "cyan"
    set h_type "pymol"
    set h_nbars 12
    set h_space 1.2
    set h_radius 0.08
    set h_arrow 0
    set h_resol 6
    set mat "Opaque"
    for {set i 0} {$i < [llength $args]} {incr i} {
        set key [lindex $args $i]
        switch -- $key {
            -mol1     { set mol1 [lindex $args [incr i]] }
            -index1   { set index1 [lindex $args [incr i]] }
            -mol2     { set mol2 [lindex $args [incr i]] }
            -index2   { set index2 [lindex $args [incr i]] }
            -color    { set color [lindex $args [incr i]] }
            -h_type   { set h_type [lindex $args [incr i]] }
            -h_nbars  { set h_nbars [lindex $args [incr i]] }
            -h_space  { set h_space [lindex $args [incr i]] }
            -h_radius { set h_radius [lindex $args [incr i]] }
            -h_arrow  { set h_arrow [lindex $args [incr i]] }
            -h_resol  { set h_resol [lindex $args [incr i]] }
            -mat      { set mat [lindex $args [incr i]] }
        }
    }
    if {$index1 eq "" || $index2 eq ""} { return }
    if {$mol1 eq "top"} { set mol1_id [molinfo top] } else { set mol1_id $mol1 }
    if {$mol2 eq "top"} { set mol2_id [molinfo top] } else { set mol2_id $mol2 }
    set sel1 [atomselect $mol1_id "index $index1"]
    set sel2 [atomselect $mol2_id "index $index2"]
    if {[$sel1 num] == 0 || [$sel2 num] == 0} {
        $sel1 delete; $sel2 delete; return
    }
    set pos1 [lindex [$sel1 get {x y z}] 0]
    set pos2 [lindex [$sel2 get {x y z}] 0]
    $sel1 delete; $sel2 delete
    set molid $mol1_id
    set before [graphics $molid list]
    graphics $molid color $color
    graphics $molid material $mat
    switch -- $h_type {
        pymol {
            set vec [vecsub $pos2 $pos1]
            set len [veclength $vec]
            if {$len < 0.001} { return }
            set dir [vecnorm $vec]
            set seg_len [expr {$len / double($h_nbars)}]
            set cyl_len [expr {$seg_len / double($h_space)}]
            for {set i 0} {$i < $h_nbars} {incr i} {
                set start [vecadd $pos1 [vecscale $dir [expr {$i * $seg_len}]]]
                set end [vecadd $start [vecscale $dir $cyl_len]]
                graphics $molid cylinder $start $end radius $h_radius resolution $h_resol
            }
            if {$h_arrow} {
                set arrow_pos [vecadd $pos2 [vecscale [vecnorm [vecsub $pos2 $pos1]] [expr {$h_radius * 3}]]]
                graphics $molid cone $pos2 $arrow_pos radius [expr {$h_radius * 2.5}] resolution $h_resol
            }
        }
        cylinder {
            graphics $molid cylinder $pos1 $pos2 radius $h_radius resolution $h_resol
            if {$h_arrow} {
                set arrow_pos [vecadd $pos2 [vecscale [vecnorm [vecsub $pos2 $pos1]] [expr {$h_radius * 3}]]]
                graphics $molid cone $pos2 $arrow_pos radius [expr {$h_radius * 2.5}] resolution $h_resol
            }
        }
        dots {
            set vec [vecsub $pos2 $pos1]
            set len [veclength $vec]
            if {$len < 0.001} { return }
            set dir [vecnorm $vec]
            set seg_len [expr {$len / double($h_nbars)}]
            for {set i 0} {$i < $h_nbars} {incr i} {
                set center [vecadd $pos1 [vecscale $dir [expr {($i + 0.5) * $seg_len}]]]
                graphics $molid sphere $center radius $h_radius resolution 12
            }
        }
        sphere {
            graphics $molid sphere $pos1 radius $h_radius resolution 12
            graphics $molid sphere $pos2 radius $h_radius resolution 12
        }
        cone {
            graphics $molid cone $pos1 $pos2 radius $h_radius resolution $h_resol
        }
        line {
            graphics $molid line $pos1 $pos2
        }
    }
    set after_ids [graphics $molid list]
    set new_ids {}
    foreach id $after_ids {
        if {[lsearch $before $id] == -1} { lappend new_ids $id }
    }
    lappend _vmd_bond_history [list $molid $new_ids]
}

proc draw_bond_undo {} {
    global _vmd_bond_history
    if {[llength $_vmd_bond_history] == 0} { return }
    set last [lindex $_vmd_bond_history end]
    set _vmd_bond_history [lrange $_vmd_bond_history 0 end-1]
    set molid [lindex $last 0]
    set ids [lindex $last 1]
    foreach id $ids { catch {graphics $molid delete $id} }
}

proc draw_bond_clear {} {
    global _vmd_bond_history
    set _vmd_bond_history {}
    foreach molid [molinfo list] { graphics $molid delete all }
}

proc make_material {name opacity} {
    if {[lsearch [material list] $name] == -1} { material add $name }
    material change opacity $name $opacity
    material change ambient $name 0.15
    material change specular $name 0.5
    material change shininess $name 0.5
    material change diffuse $name 0.85
}
"""


def _style_tcl(dg_inter_name, sl2r_name, iso_inter, style_name, shade_mode="full", keep_h_indices=None):
    """生成 IGMH 的 VMD TCL 脚本。
    keep_h_indices: 要保留的氢原子序号列表（从0开始），None=保留所有，[]=删除所有
    """
    s = STYLES.get(style_name, STYLES["sob-art"])

    light_lines = ""
    for k, v in s["lights"].items():
        light_lines += f"light {k} {v}\n"

    if shade_mode == "medium":
        shadow_on, ao_on = True, False
    else:
        shadow_on = s["shadows"] == "on"
        ao_on = s["ao"] == "on"
    shadow_lines = f"display shadows {'on' if shadow_on else 'off'}\n"
    shadow_lines += f"display ambientocclusion {'on' if ao_on else 'off'}\n"
    shadow_lines += "display aoambient 0.8\ndisplay aodirect 0.3\n"

    mat_names = ["ambient", "diffuse", "specular", "shininess", "mirror", "opacity", "outline", "outlinewidth", "transmode"]

    mat_surf_lines = "if {[lsearch [material list] _igmh_surf] < 0} {material add _igmh_surf}\n"
    for name, val in zip(mat_names, s["surface_mat"]):
        mat_surf_lines += f"material change {name} _igmh_surf {val}\n"

    atom_mat_lines = "if {[lsearch [material list] _stl_atom] < 0} {material add _stl_atom}\n"
    for name, val in zip(mat_names, s["atom_mat"]):
        atom_mat_lines += f"material change {name} _stl_atom {val}\n"

    tcl = f"""color Display Background white
axes location Off
display depthcue off
display projection Orthographic
display rendermode GLSL

{light_lines}
{shadow_lines}

# ── 加载：sl2r 先加载（dataset 0），dg_inter 后加载（dataset 1）──
mol new {sl2r_name} type cube first 0 last 0 step 1 waitfor all
mol addfile {dg_inter_name} type cube first 0 last 0 step 1 waitfor all

# 删除 sl2r 的默认 VDW rep
mol delrep 0 top

# rep 0: CPK 原子（坐标来自 sl2r.cub）
mol representation CPK {s['atom_cpk']}
mol addrep top
mol modstyle 0 top CPK {s['atom_cpk']}
mol modmaterial 0 top _stl_atom
{atom_mat_lines}
mol modcolor 0 top Element
{_gview_color_tcl(exclude={'C'})}
color Element C {s['c_color']}
color change rgb {s['c_color']} {s['c_rgb']}

# ── 额外美化设置（来自 igmh-right-new2.py）────────────────
material change mirror Opaque 0.15
material change outline Opaque 4.000000
material change outlinewidth Opaque 0.5
material change ambient Glossy 0.1
material change diffuse Glossy 0.600000
material change opacity Glossy 0.75
material change shininess Glossy 1.0
display distance -7.0
display height 10
light 3 on

# ── 材质定义（必须在 addrep 之前）────────────────
color scale method BGR
{mat_surf_lines}

# rep 1: dg_inter 的 δg 等值面，颜色由 sl2r 值映射
#   先 addrep 创建空 rep，再用 modstyle/modcolor 精确控制
#   避免用 mol representation / mol color 修改默认值影响 rep 0
mol addrep top
mol modstyle 1 top Isosurface {iso_inter} 1 0 0 1 1
mol modcolor 1 top Volume 0
mol scaleminmax top 1 -0.05 0.05
mol modmaterial 1 top _igmh_surf
"""

    if keep_h_indices is not None:
        if keep_h_indices:
            h_idx_list = " ".join(map(str, keep_h_indices))
            h_sel_str = f"not element H or (element H and index {h_idx_list})"
        else:
            h_sel_str = "not element H"
        h_filter_code = f"""
# 隐藏氢原子（只影响原子球棍 rep 0）
mol modselect 0 top "{h_sel_str}"
"""
    else:
        h_filter_code = ""

    return tcl.rstrip() + "\n" + h_filter_code


# ── VMD 预览 ──────────────────────────────────────────────
def preview_igmh(dg_inter_path, sl2r_path, iso_inter=0.01,
                 style_name="sob-art", vmd_exe=None, shade_mode="full",
                 keep_h_indices=None):
    """打开 VMD GUI 预览两个 cube 文件，返回 (port, render_dir)。"""
    if vmd_exe is None:
        vmd_exe = DEFAULT_VMD

    dg_name = os.path.basename(dg_inter_path)
    sl_name = os.path.basename(sl2r_path)
    work_dir = os.path.dirname(os.path.abspath(dg_inter_path))

    try:
        dg_inter_path.encode("ascii")
        sl2r_path.encode("ascii")
        has_nonascii = False
    except UnicodeEncodeError:
        has_nonascii = True

    if has_nonascii:
        render_dir = tempfile.mkdtemp(prefix="vmd_igmh_")
        shutil.copy2(dg_inter_path, os.path.join(render_dir, dg_name))
        shutil.copy2(sl2r_path, os.path.join(render_dir, sl_name))
    else:
        render_dir = work_dir

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    style_tcl = _style_tcl(dg_name, sl_name, iso_inter, style_name, shade_mode,
                           keep_h_indices=keep_h_indices)
    socket_tcl = f"""
# === Socket 服务器 ===
set serverSocket [socket -server _vmd_accept -myaddr 127.0.0.1 {port}]
proc _vmd_accept {{chan addr port}} {{
    fconfigure $chan -buffering line -translation binary
    fileevent $chan readable [list _vmd_handle $chan]
}}

proc _vmd_handle {{chan}} {{
    if [eof $chan] {{
        close $chan
        return
    }}
    gets $chan cmd
    if {{{{
        $cmd eq ""
    }}}} return

    if [catch {{uplevel #0 $cmd}} err] {{
        puts $chan "ERROR: $err"
    }} else {{
        puts $chan "OK"
    }}
    flush $chan
}}

puts "==========================================="
puts " IGMH 预览已就绪 (样式: {style_name})"
puts " 端口: {port}"
puts "==========================================="
"""
    tcl = _draw_bond_tcl() + style_tcl + socket_tcl
    tcl_path = os.path.join(render_dir, "_igmh_preview.tcl")
    with open(tcl_path, "w") as f:
        f.write(tcl)

    subprocess.Popen(
        [vmd_exe, "-e", "_igmh_preview.tcl"],
        cwd=render_dir,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )

    return port, render_dir


# ── 通过 socket 渲染当前视角 ─────────────────────────────
def render_current_view(port, render_dir, output_png=None,
                        tachyon_exe=None, resolution=(2000, 1500),
                        style_name="sob-art", shade_mode="full"):
    """连接 VMD socket，发送 render Tachyon 命令，Tachyon 渲染成 PNG。"""
    if tachyon_exe is None:
        tachyon_exe = DEFAULT_TACHYON
    s = STYLES.get(style_name, STYLES["sob-art"])

    vmd_sock = None
    for attempt in range(10):
        try:
            vmd_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            vmd_sock.settimeout(3)
            vmd_sock.connect(("127.0.0.1", port))
            break
        except (ConnectionRefusedError, socket.timeout, OSError):
            time.sleep(0.5)
            if vmd_sock:
                vmd_sock.close()
            vmd_sock = None

    if vmd_sock is None:
        print("  无法连接 VMD")
        return None

    def send_cmd(cmd):
        vmd_sock.sendall((cmd + "\n").encode("utf-8"))
        time.sleep(0.3)
        resp = b""
        vmd_sock.settimeout(2)
        try:
            while True:
                chunk = vmd_sock.recv(4096)
                if not chunk:
                    break
                resp += chunk
                if b"\n" in resp:
                    break
        except socket.timeout:
            pass
        return resp.decode("utf-8", errors="replace").strip()

    for fn in ["vmdscene.dat", "_render.bmp"]:
        fp = os.path.join(render_dir, fn)
        if os.path.exists(fp):
            os.remove(fp)

    resp = send_cmd("render Tachyon vmdscene.dat")
    vmd_sock.close()

    dat = os.path.join(render_dir, "vmdscene.dat")
    if not os.path.exists(dat):
        return None

    shade_flag = "-fullshade" if shade_mode == "full" else "-mediumshade"
    bmp_name = "_render.bmp"
    args = [
        tachyon_exe, "vmdscene.dat",
        "-format", "BMP", "-o", bmp_name,
        "-res", str(resolution[0]), str(resolution[1]),
        "-numthreads", "4", "-aasamples", "24",
        shade_flag,
    ]
    if s["tachyon_options"]:
        extra = s["tachyon_options"].split()
        args.extend(extra)

    try:
        subprocess.run(
            args, capture_output=True, cwd=render_dir, timeout=600,
            encoding="utf-8", errors="replace",
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None

    bmp = os.path.join(render_dir, bmp_name)
    if not os.path.exists(bmp):
        return None

    if output_png is None:
        output_png = os.path.join(render_dir, "igmh_render.png")

    try:
        from PIL import Image
        img = Image.open(bmp)
        img.save(output_png)
    except ImportError:
        output_png = bmp

    return output_png


# ── 自动渲染（无预览）─────────────────────────────────────
def render_igmh_auto(dg_inter_path, sl2r_path, output_png=None,
                     iso_inter=0.01,
                     vmd_exe=None, tachyon_exe=None,
                     resolution=(2000, 1500), style_name="sob-art", shade_mode="full",
                     keep_h_indices=None):
    """自动渲染（不打开 VMD GUI），用于批量模式。"""
    if vmd_exe is None:
        vmd_exe = DEFAULT_VMD
    if tachyon_exe is None:
        tachyon_exe = DEFAULT_TACHYON
    if output_png is None:
        stem = os.path.splitext(os.path.basename(dg_inter_path))[0]
        output_png = stem + "_igmh.png"

    dg_name = os.path.basename(dg_inter_path)
    sl_name = os.path.basename(sl2r_path)
    work_dir = os.path.dirname(os.path.abspath(dg_inter_path))

    try:
        dg_inter_path.encode("ascii")
        sl2r_path.encode("ascii")
        has_nonascii = False
    except UnicodeEncodeError:
        has_nonascii = True

    if has_nonascii:
        tmp_dir = tempfile.mkdtemp(prefix="vmd_igmh_")
        shutil.copy2(dg_inter_path, os.path.join(tmp_dir, dg_name))
        shutil.copy2(sl2r_path, os.path.join(tmp_dir, sl_name))
        render_dir = tmp_dir
    else:
        render_dir = work_dir

    s = STYLES.get(style_name, STYLES["sob-art"])
    style_tcl = _style_tcl(dg_name, sl_name, iso_inter, style_name, shade_mode,
                           keep_h_indices=keep_h_indices)
    tcl = style_tcl + "render Tachyon vmdscene.dat\nquit\n"

    tcl_path = os.path.join(render_dir, "_igmh_auto.tcl")
    with open(tcl_path, "w") as f:
        f.write(tcl)

    for fn in ["vmdscene.dat"]:
        fp = os.path.join(render_dir, fn)
        if os.path.exists(fp):
            os.remove(fp)

    try:
        subprocess.run(
            [vmd_exe, "-dispdev", "text", "-e", "_igmh_auto.tcl"],
            capture_output=True, cwd=render_dir, timeout=120,
            encoding="utf-8", errors="replace",
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        if has_nonascii:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        return None

    dat = os.path.join(render_dir, "vmdscene.dat")
    if not os.path.exists(dat):
        if has_nonascii:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        return None

    shade_flag = "-fullshade" if shade_mode == "full" else "-mediumshade"
    bmp_name = "_render.bmp"
    args = [
        tachyon_exe, "vmdscene.dat",
        "-format", "BMP", "-o", bmp_name,
        "-res", str(resolution[0]), str(resolution[1]),
        "-numthreads", "4", "-aasamples", "24",
        shade_flag,
    ]
    if s["tachyon_options"]:
        extra = s["tachyon_options"].split()
        args.extend(extra)

    try:
        subprocess.run(
            args, capture_output=True, cwd=render_dir, timeout=600,
            encoding="utf-8", errors="replace",
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        if has_nonascii:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        return None

    bmp = os.path.join(render_dir, bmp_name)
    if not os.path.exists(bmp):
        if has_nonascii:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        return None

    try:
        from PIL import Image
        img = Image.open(bmp)
        img.save(output_png)
    except ImportError:
        output_png = bmp

    for fn in ["vmdscene.dat", "_igmh_auto.tcl", bmp_name]:
        fp = os.path.join(render_dir, fn)
        if os.path.exists(fp):
            os.remove(fp)
    if has_nonascii:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return output_png


# ── GUI ───────────────────────────────────────────────────
def launch_gui():
    import tkinter as tk
    from tkinter import filedialog, ttk, messagebox

    paths = load_config()

    class App:
        def __init__(self, root):
            self.root = root
            self.root.title("IGMH 等值面可视化 — VMD/Tachyon")
            self.root.geometry("780x750")
            self.running = False

            self.vmd_port = None
            self.vmd_render_dir = None
            self.vmd_dg_path = None
            self.vmd_sl_path = None

            frm0 = ttk.LabelFrame(root, text="软件路径")
            frm0.pack(fill="x", padx=10, pady=(5, 2))

            r_vmd = ttk.Frame(frm0); r_vmd.pack(fill="x", padx=5, pady=2)
            ttk.Label(r_vmd, text="VMD:").pack(side="left")
            self.var_vmd = tk.StringVar(value=paths["vmd"])
            ttk.Entry(r_vmd, textvariable=self.var_vmd, width=52).pack(
                side="left", fill="x", expand=True, padx=3)
            ttk.Button(r_vmd, text="浏览", width=5,
                       command=lambda: self._browse_exe("vmd")).pack(side="left")

            frm1 = ttk.LabelFrame(root, text="Cube 文件（由 Multiwfn IGMH 分析生成）")
            frm1.pack(fill="x", padx=10, pady=2)

            r_dg = ttk.Frame(frm1); r_dg.pack(fill="x", padx=5, pady=2)
            ttk.Label(r_dg, text="dg_inter.cub:", width=14, anchor="e").pack(side="left")
            self.var_dg = tk.StringVar()
            ttk.Entry(r_dg, textvariable=self.var_dg, width=45).pack(
                side="left", fill="x", expand=True, padx=3)
            ttk.Button(r_dg, text="浏览", width=5,
                       command=lambda: self._browse_cub("dg")).pack(side="left", padx=2)

            r_sl = ttk.Frame(frm1); r_sl.pack(fill="x", padx=5, pady=2)
            ttk.Label(r_sl, text="sl2r.cub:", width=14, anchor="e").pack(side="left")
            self.var_sl = tk.StringVar()
            ttk.Entry(r_sl, textvariable=self.var_sl, width=45).pack(
                side="left", fill="x", expand=True, padx=3)
            ttk.Button(r_sl, text="浏览", width=5,
                       command=lambda: self._browse_cub("sl")).pack(side="left", padx=2)

            r_auto = ttk.Frame(frm1); r_auto.pack(fill="x", padx=5, pady=2)
            ttk.Button(r_auto, text="自动匹配（选择文件夹，自动查找 dg_inter.cub 和 sl2r.cub）",
                       command=self._auto_match).pack(side="left")

            frm2 = ttk.LabelFrame(root, text="参数")
            frm2.pack(fill="x", padx=10, pady=2)

            r1 = ttk.Frame(frm2); r1.pack(fill="x", padx=5, pady=2)
            ttk.Label(r1, text="δg_inter:").pack(side="left")
            self.var_iso_inter = tk.StringVar(value="0.01")
            ttk.Entry(r1, textvariable=self.var_iso_inter, width=6).pack(side="left", padx=5)
            ttk.Label(r1, text="样式:").pack(side="left", padx=(10, 0))
            style_names = list(STYLES.keys())
            style_display = [f"{n}  ({STYLES[n]['desc']})" for n in style_names]
            self.var_style = tk.StringVar(value=style_display[0])
            self.style_combo = ttk.Combobox(r1, textvariable=self.var_style,
                                            width=30, values=style_display, state="readonly")
            self.style_combo.pack(side="left", padx=5)
            self.style_combo.current(0)

            r2 = ttk.Frame(frm2); r2.pack(fill="x", padx=5, pady=2)
            ttk.Label(r2, text="分辨率:").pack(side="left")
            self.var_res = tk.StringVar(value="2000x1500")
            ttk.Combobox(r2, textvariable=self.var_res, width=10,
                         values=["2000x1500", "1200x900", "3000x2250"],
                         state="readonly").pack(side="left", padx=5)
            self.var_shade = tk.StringVar(value="full")
            ttk.Label(r2, text="光影:").pack(side="left", padx=(10, 0))
            for text, val in [("Full", "full"), ("Medium", "medium")]:
                ttk.Radiobutton(r2, text=text, variable=self.var_shade,
                                value=val).pack(side="left", padx=3)
            self.var_auto_render = tk.BooleanVar(value=False)
            ttk.Checkbutton(r2, text="自动渲染", variable=self.var_auto_render).pack(side="left", padx=(15, 0))
            self.var_open = tk.BooleanVar(value=False)
            ttk.Checkbutton(r2, text="完成后打开文件夹", variable=self.var_open).pack(side="left", padx=(10, 0))

            r_h = ttk.Frame(frm2); r_h.pack(fill="x", padx=5, pady=2)
            self.var_hide_h = tk.BooleanVar(value=False)
            self.btn_h_filter = ttk.Button(r_h, text="隐藏所有H", width=9,
                                           command=self._toggle_h_filter, state="disabled")
            self.btn_h_filter.pack(side="left")
            ttk.Label(r_h, text=" 保留序号:").pack(side="left", padx=(6, 0))
            self.var_h_indices = tk.StringVar(value="")
            ttk.Entry(r_h, textvariable=self.var_h_indices, width=14).pack(side="left", padx=2)
            ttk.Label(r_h, text="(逗号分隔，空=全隐藏)").pack(side="left")

            frm3 = ttk.LabelFrame(root, text="输出与操作")
            frm3.pack(fill="x", padx=10, pady=2)
            self.var_out = tk.StringVar()
            ttk.Label(frm3, text="输出:").pack(side="left", padx=(5, 0), pady=5)
            ttk.Entry(frm3, textvariable=self.var_out, width=35).pack(
                side="left", fill="x", expand=True, padx=3, pady=5)
            ttk.Button(frm3, text="浏览", command=self._browse_out, width=5).pack(
                side="left", padx=2, pady=5)
            self.btn_run = ttk.Button(frm3, text="  预览  ", command=self._preview)
            self.btn_run.pack(side="left", padx=3, pady=5)
            self.btn_render = ttk.Button(frm3, text="  渲染当前视角  ", command=self._render_view,
                                         state="disabled")
            self.btn_render.pack(side="left", padx=3, pady=5)
            self.btn_auto = ttk.Button(frm3, text="  自动渲染  ", command=self._auto_render)
            self.btn_auto.pack(side="left", padx=3, pady=5)
            self.btn_stop = ttk.Button(frm3, text="  停止  ", command=self._stop,
                                       state="disabled")
            self.btn_stop.pack(side="left", padx=3, pady=5)

            frm5 = ttk.LabelFrame(root, text="画虚线 (预览后可用)")
            frm5.pack(fill="x", padx=10, pady=5)

            self.bond_colors = {
                "黑色": "black", "灰色": "gray", "青色": "cyan", "黄色": "yellow",
                "红色": "red", "蓝色": "blue", "绿色": "green", "白色": "white"}
            self.bond_types = {
                "虚线(pymol)": "pymol", "圆点(dots)": "dots",
                "实线圆柱": "cylinder", "球体": "sphere",
                "箭头(cone)": "cone", "细线(line)": "line"}
            self.bond_mats = {
                "不透明": "Opaque", "50%透明": "HalfTransparent",
                "透明": "Transparent"}

            f_bond = ttk.Frame(frm5); f_bond.pack(fill="x", padx=5, pady=2)
            ttk.Label(f_bond, text="原子1:").pack(side="left")
            self.var_bond_atom1 = tk.StringVar(value="0")
            ttk.Entry(f_bond, textvariable=self.var_bond_atom1, width=6).pack(side="left", padx=2)
            ttk.Label(f_bond, text="原子2:").pack(side="left", padx=(8, 0))
            self.var_bond_atom2 = tk.StringVar(value="1")
            ttk.Entry(f_bond, textvariable=self.var_bond_atom2, width=6).pack(side="left", padx=2)

            ttk.Label(f_bond, text="颜色:").pack(side="left", padx=(8, 0))
            self.var_bond_color = tk.StringVar(value="灰色")
            ttk.Combobox(f_bond, textvariable=self.var_bond_color, width=6,
                         values=list(self.bond_colors.keys()),
                         state="readonly").pack(side="left", padx=2)

            ttk.Label(f_bond, text="类型:").pack(side="left", padx=(8, 0))
            self.var_bond_type = tk.StringVar(value="圆点(dots)")
            ttk.Combobox(f_bond, textvariable=self.var_bond_type, width=10,
                         values=list(self.bond_types.keys()),
                         state="readonly").pack(side="left", padx=2)

            ttk.Label(f_bond, text="材质:").pack(side="left", padx=(8, 0))
            self.var_bond_mat = tk.StringVar(value="50%透明")
            ttk.Combobox(f_bond, textvariable=self.var_bond_mat, width=8,
                         values=list(self.bond_mats.keys()),
                         state="readonly").pack(side="left", padx=2)

            f_bond2 = ttk.Frame(frm5); f_bond2.pack(fill="x", padx=5, pady=2)
            ttk.Label(f_bond2, text="段数:").pack(side="left")
            self.var_bond_nbars = tk.StringVar(value="10")
            ttk.Entry(f_bond2, textvariable=self.var_bond_nbars, width=5).pack(side="left", padx=2)
            ttk.Label(f_bond2, text="间距:").pack(side="left", padx=(6, 0))
            self.var_bond_space = tk.StringVar(value="1.2")
            ttk.Entry(f_bond2, textvariable=self.var_bond_space, width=5).pack(side="left", padx=2)
            ttk.Label(f_bond2, text="半径:").pack(side="left", padx=(6, 0))
            self.var_bond_radius = tk.StringVar(value="0.06")
            ttk.Entry(f_bond2, textvariable=self.var_bond_radius, width=5).pack(side="left", padx=2)

            self.btn_draw_bond = ttk.Button(f_bond2, text="  画虚线  ",
                                            command=self._draw_bond, state="disabled")
            self.btn_draw_bond.pack(side="left", padx=(12, 2))
            self.btn_undo_bond = ttk.Button(f_bond2, text="撤销", command=self._undo_bond,
                                            state="disabled")
            self.btn_undo_bond.pack(side="left", padx=2)
            self.btn_clear_bond = ttk.Button(f_bond2, text="清除全部", command=self._clear_bond,
                                              state="disabled")
            self.btn_clear_bond.pack(side="left", padx=2)

            self.var_prog = tk.StringVar(value="就绪")
            ttk.Label(root, textvariable=self.var_prog).pack(fill="x", padx=10)

            self.log = tk.Text(root, height=6, font=("Consolas", 9),
                               bg="#1e1e1e", fg="#d4d4d4", insertbackground="white")
            self.log.pack(fill="both", expand=True, padx=10, pady=5)

            self.current_iso_inter = 0.01
            self.current_opacity = None
            self.iso_step = 0.001
            self.opacity_step = 0.05

            root.bind("<Prior>", self._key_iso_inter_up)
            root.bind("<Next>", self._key_iso_inter_down)
            root.bind("<Home>", self._key_opacity_up)
            root.bind("<End>", self._key_opacity_down)

        def _get_style_name(self):
            val = self.var_style.get().strip()
            if val:
                return val.split("  ")[0].strip()
            return "sob-art"

        def _browse_exe(self, which):
            p = filedialog.askopenfilename(title="选择 VMD 可执行文件",
                filetypes=[("Executable", "*.exe")])
            if p:
                self.var_vmd.set(p)

        def _save_paths(self):
            vmd = self.var_vmd.get().strip()
            tachyon = os.path.join(os.path.dirname(vmd), "tachyon_WIN32.exe")
            save_config(vmd, tachyon)

        def _get_paths(self):
            vmd = self.var_vmd.get().strip()
            tachyon = os.path.join(os.path.dirname(vmd), "tachyon_WIN32.exe")
            return {"vmd": vmd, "tachyon": tachyon}

        def _browse_cub(self, which):
            p = filedialog.askopenfilename(
                title="选择 cube 文件",
                filetypes=[("Cube files", "*.cub *.cube"), ("All", "*.*")])
            if p:
                if which == "dg":
                    self.var_dg.set(p)
                else:
                    self.var_sl.set(p)

        def _auto_match(self):
            d = filedialog.askdirectory(title="选择含 cube 文件的文件夹")
            if not d:
                return
            for f in os.listdir(d):
                fl = f.lower()
                if fl in ("dg_inter.cub", "dg_inter.cube"):
                    self.var_dg.set(os.path.join(d, f))
                elif fl in ("sl2r.cub", "sl2r.cube"):
                    self.var_sl.set(os.path.join(d, f))
            if not self.var_dg.get() and not self.var_sl.get():
                messagebox.showwarning("提示", "未找到 dg_inter.cub 或 sl2r.cub")

        def _browse_out(self):
            p = filedialog.askdirectory(title="选择输出目录")
            if p:
                self.var_out.set(p)

        def _append(self, msg):
            self.log.insert("end", msg + "\n")
            self.log.see("end")
            self.root.update_idletasks()

        def _get_params(self):
            try:
                iso_inter = float(self.var_iso_inter.get().strip())
            except ValueError:
                iso_inter = 0.01
            style_name = self._get_style_name()
            try:
                res_str = self.var_res.get().strip()
                w, h = res_str.split("x")
                resolution = (int(w), int(h))
            except (ValueError, AttributeError):
                resolution = (2000, 1500)
            h_str = self.var_h_indices.get().strip()
            if self.var_hide_h.get() or h_str:
                if h_str:
                    try:
                        keep_h_indices = [int(x.strip()) for x in h_str.split(",") if x.strip()]
                    except ValueError:
                        keep_h_indices = []
                else:
                    keep_h_indices = []
            else:
                keep_h_indices = None
            return iso_inter, style_name, resolution, self.var_shade.get(), keep_h_indices

        def _validate(self):
            dg = self.var_dg.get().strip()
            sl = self.var_sl.get().strip()
            if not dg:
                messagebox.showwarning("提示", "请选择 dg_inter.cub")
                return None
            if not sl:
                messagebox.showwarning("提示", "请选择 sl2r.cub")
                return None
            if not os.path.isfile(dg):
                messagebox.showwarning("路径错误", f"dg_inter.cub 不存在:\n{dg}")
                return None
            if not os.path.isfile(sl):
                messagebox.showwarning("路径错误", f"sl2r.cub 不存在:\n{sl}")
                return None
            exe_paths = self._get_paths()
            if not os.path.exists(exe_paths["vmd"]):
                messagebox.showwarning("路径错误", f"VMD 不存在:\n{exe_paths['vmd']}")
                return None
            self._save_paths()
            return dg, sl, exe_paths

        def _preview(self):
            result = self._validate()
            if not result:
                return
            dg, sl, exe_paths = result

            iso_inter, style_name, resolution, shade_mode, keep_h_indices = self._get_params()

            self.vmd_dg_path = dg
            self.vmd_sl_path = sl
            self.current_iso_inter = iso_inter
            self.current_opacity = None

            self._append(f"\n启动 VMD 预览...")
            self._append(f"  dg_inter: {os.path.basename(dg)}  iso={iso_inter}")
            self._append(f"  sl2r:     {os.path.basename(sl)}  (用于 Volume 着色)")
            self._append(f"  样式: {style_name}")
            self._append("请在 VMD 中调整视角，然后点击 [渲染当前视角]")

            try:
                port, render_dir = preview_igmh(
                    dg, sl, iso_inter=iso_inter,
                    style_name=style_name, vmd_exe=exe_paths["vmd"],
                    shade_mode=shade_mode, keep_h_indices=keep_h_indices)
                if port:
                    self.vmd_port = port
                    self.vmd_render_dir = render_dir
                    self.btn_render.config(state="normal")
                    self.btn_h_filter.config(state="normal")
                    self.btn_draw_bond.config(state="normal")
                    self.btn_undo_bond.config(state="normal")
                    self.btn_clear_bond.config(state="normal")
                    self._append(f"VMD 已启动 (端口 {port})，等待操作...")
                else:
                    self._append("VMD 启动失败")
            except Exception as e:
                self._append(f"VMD 启动错误: {e}")

        def _render_view(self):
            if not self.vmd_port or not self.vmd_render_dir:
                messagebox.showwarning("提示", "请先点击 [预览] 打开 VMD")
                return

            out = self.var_out.get().strip()
            if out and not os.path.isdir(out):
                os.makedirs(out, exist_ok=True)

            _, style_name, resolution, shade_mode, _ = self._get_params()
            exe_paths = self._get_paths()

            output_png = None
            if self.vmd_dg_path:
                stem = os.path.splitext(os.path.basename(self.vmd_dg_path))[0]
                if out:
                    output_png = os.path.join(out, f"{stem}_igmh.png")
                else:
                    output_png = os.path.join(
                        os.path.dirname(self.vmd_dg_path), f"{stem}_igmh.png")

            def render_worker():
                self.btn_render.config(state="disabled")
                self._append(f"\n正在渲染当前视角 (样式: {style_name})...")
                t0 = time.time()
                try:
                    png = render_current_view(
                        self.vmd_port, self.vmd_render_dir,
                        output_png=output_png,
                        tachyon_exe=exe_paths["tachyon"],
                        resolution=resolution, style_name=style_name,
                        shade_mode=shade_mode,
                    )
                    dt = time.time() - t0
                    if png:
                        self._append(f"渲染完成 ({dt:.1f}s) -> {os.path.basename(png)}")
                        os.startfile(png)
                    else:
                        self._append(f"渲染失败 ({dt:.1f}s)")
                except Exception as e:
                    self._append(f"渲染错误: {e}")
                self.btn_render.config(state="normal")

            threading.Thread(target=render_worker, daemon=True).start()

        def _auto_render(self):
            result = self._validate()
            if not result:
                return
            dg, sl, exe_paths = result

            iso_inter, style_name, resolution, shade_mode, keep_h_indices = self._get_params()
            do_open = self.var_open.get()

            def worker():
                self.btn_auto.config(state="disabled")
                self.btn_stop.config(state="normal")
                self.running = True
                t0 = time.time()
                self._append(f"\n自动渲染: {os.path.basename(dg)} + {os.path.basename(sl)}")
                self._append(f"  δg_inter={iso_inter}  样式={style_name}")

                out = self.var_out.get().strip() or os.path.dirname(os.path.abspath(dg))
                os.makedirs(out, exist_ok=True)
                stem = os.path.splitext(os.path.basename(dg))[0]
                output_png = os.path.join(out, f"{stem}_igmh.png")

                try:
                    png = render_igmh_auto(
                        dg, sl, output_png=output_png,
                        iso_inter=iso_inter,
                        style_name=style_name, resolution=resolution,
                        vmd_exe=exe_paths["vmd"],
                        tachyon_exe=exe_paths["tachyon"],
                        shade_mode=shade_mode,
                        keep_h_indices=keep_h_indices,
                    )
                    dt = time.time() - t0
                    if png:
                        self._append(f"完成 ({dt:.1f}s) -> {os.path.basename(png)}")
                        if do_open:
                            os.startfile(png)
                    else:
                        self._append(f"失败 ({dt:.1f}s)")
                except Exception as e:
                    self._append(f"错误: {e}")

                self.running = False
                self.btn_auto.config(state="normal")
                self.btn_stop.config(state="disabled")

            threading.Thread(target=worker, daemon=True).start()

        def _stop(self):
            self.running = False
            self.btn_stop.config(state="disabled")

        def _send_vmd_cmd(self, cmd):
            if not self.vmd_port:
                return None
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                sock.connect(("127.0.0.1", self.vmd_port))
                sock.sendall((cmd + "\n").encode("utf-8"))
                time.sleep(0.2)
                resp = b""
                sock.settimeout(2)
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
                sock.close()
                return resp.decode("utf-8", errors="replace").strip()
            except Exception:
                return None

        def _key_iso_inter_up(self, event=None):
            self.current_iso_inter = round(min(self.current_iso_inter + self.iso_step, 0.5), 4)
            self._apply_iso_inter_change()

        def _key_iso_inter_down(self, event=None):
            self.current_iso_inter = round(max(self.current_iso_inter - self.iso_step, 0.0001), 4)
            self._apply_iso_inter_change()

        def _key_opacity_up(self, event=None):
            if self.current_opacity is None:
                style = STYLES.get(self._get_style_name(), STYLES["sob-art"])
                self.current_opacity = style["surface_mat"][5]
            self.current_opacity = round(min(self.current_opacity + self.opacity_step, 1.0), 2)
            self._apply_opacity_change()

        def _key_opacity_down(self, event=None):
            if self.current_opacity is None:
                style = STYLES.get(self._get_style_name(), STYLES["sob-art"])
                self.current_opacity = style["surface_mat"][5]
            self.current_opacity = round(max(self.current_opacity - self.opacity_step, 0.05), 2)
            self._apply_opacity_change()

        def _apply_iso_inter_change(self):
            iso = self.current_iso_inter
            self.var_iso_inter.set(f"{iso:.4g}")
            cmd = f"mol modstyle 1 top Isosurface {iso} 1 0 0 1 1"
            resp = self._send_vmd_cmd(cmd)
            status = "OK" if resp and "ERROR" not in resp else "VMD 未连接"
            self._append(f"[δg_inter] iso = {iso:.4g}  ({status})")

        def _apply_opacity_change(self):
            op = self.current_opacity
            cmd = f"material change opacity _igmh_surf {op}"
            self._send_vmd_cmd(cmd)
            self._append(f"[透明度] opacity = {op:.2f}")

        def _toggle_h_filter(self):
            if not self.vmd_port:
                self._append("请先点击预览按钮启动 VMD")
                return

            self.var_hide_h.set(not self.var_hide_h.get())
            if self.var_hide_h.get():
                self.btn_h_filter.config(text="显示所有氢原子")
                h_str = self.var_h_indices.get().strip()
                if h_str:
                    try:
                        keep_indices = [int(x.strip()) for x in h_str.split(",") if x.strip()]
                        idx_str = " ".join(map(str, keep_indices))
                        sel_str = f"not element H or (element H and index {idx_str})"
                    except ValueError:
                        sel_str = "not element H"
                else:
                    sel_str = "not element H"
                cmd = f'mol modselect 0 top "{sel_str}"'
                self._send_vmd_cmd(cmd)
                self._append("[隐藏氢] 已隐藏氢原子")
            else:
                self.btn_h_filter.config(text="隐藏所有H")
                cmd = 'mol modselect 0 top all'
                self._send_vmd_cmd(cmd)
                self._append("[隐藏氢] 已恢复所有氢原子")

        def _draw_bond(self):
            if not self.vmd_port:
                messagebox.showwarning("提示", "请先点击 [预览] 打开 VMD")
                return
            a1 = self.var_bond_atom1.get().strip()
            a2 = self.var_bond_atom2.get().strip()
            if not a1 or not a2:
                messagebox.showwarning("提示", "请输入两个原子索引")
                return
            color = self.bond_colors.get(self.var_bond_color.get(), "gray")
            btype = self.bond_types.get(self.var_bond_type.get(), "dots")
            mat = self.bond_mats.get(self.var_bond_mat.get(), "HalfTransparent")
            nbars = self.var_bond_nbars.get().strip() or "10"
            space = self.var_bond_space.get().strip() or "1.2"
            radius = self.var_bond_radius.get().strip() or "0.06"

            if btype == "cylinder":
                cmd = (f"draw_bond -mol1 top -index1 {a1} -mol2 top -index2 {a2} "
                       f"-color {color} -h_type {btype} -h_radius {radius} -mat {mat}")
            else:
                cmd = (f"draw_bond -mol1 top -index1 {a1} -mol2 top -index2 {a2} "
                       f"-h_nbars {nbars} -h_space {space} -h_radius {radius} "
                       f"-color {color} -h_type {btype} -mat {mat}")
            resp = self._send_vmd_cmd(cmd)
            if resp and "ERROR" not in resp:
                self._append(f"[画虚线] 原子{a1}-{a2} {color} {btype} {mat}")
                self.btn_undo_bond.config(state="normal")
            else:
                self._append("[画虚线] 失败")

        def _undo_bond(self):
            resp = self._send_vmd_cmd("draw_bond_undo")
            if resp and "ERROR" not in resp:
                self._append("[虚线] 撤销")
            else:
                self._append("[虚线] 撤销失败")

        def _clear_bond(self):
            resp = self._send_vmd_cmd("draw_bond_clear")
            if resp and "ERROR" not in resp:
                self._append("[虚线] 清除全部")
            else:
                self._append("[虚线] 清除失败")

    root = tk.Tk()
    App(root)
    root.mainloop()


# ── 命令行入口 ────────────────────────────────────────────
def main():
    if len(sys.argv) > 1:
        import argparse
        p = argparse.ArgumentParser(description="IGMH 等值面可视化工具")
        p.add_argument("dg_inter", help="dg_inter.cub 文件路径")
        p.add_argument("sl2r", help="sl2r.cub 文件路径")
        p.add_argument("--iso", type=float, default=0.01, help="δg_inter 等值面阈值")
        p.add_argument("--style", default="sob-art",
                       choices=list(STYLES.keys()), help="渲染样式")
        p.add_argument("--res", default="2000,1500", help="分辨率 宽,高")
        p.add_argument("--out", default=None, help="输出 PNG 路径")
        a = p.parse_args()

        w, h = [int(x) for x in a.res.split(",")]
        output_png = a.out or os.path.splitext(a.dg_inter)[0] + "_igmh.png"

        print(f"渲染 IGMH: {os.path.basename(a.dg_inter)} + {os.path.basename(a.sl2r)}")
        print(f"  δg_inter={a.iso}  样式={a.style}  分辨率={w}x{h}")

        png = render_igmh_auto(
            a.dg_inter, a.sl2r, output_png=output_png,
            iso_inter=a.iso,
            style_name=a.style, resolution=(w, h)
        )
        if png:
            print(f"完成 -> {os.path.basename(png)}")
        else:
            print("失败")
    else:
        launch_gui()


if __name__ == "__main__":
    main()