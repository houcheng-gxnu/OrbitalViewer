#!/usr/bin/env python3
"""
fchk 轨道等值面可视化工具 v5.0 (Multi-Orbital Support)
Multiwfn (fchk -> cube) + VMD (预览 + Tachyon 渲染) + Tachyon (scene -> BMP/PNG)

作者：Workbuddy + Trae AI
开发方式：人机协作开发
开发时间：2026年5月，耗时约1小时

致谢：
  - Multiwfn (sobereva)：强大的量子化学波函数分析软件
  - vcube2.0 (钟诚)：提供11种精美渲染样式配置
  - VMD & Tachyon：分子可视化与光线追踪渲染引擎

特性：
  - 集成 vcube2.0 (钟诚) 的 11 种渲染样式
  - VMD GUI 预览 -> 手动调整视角 -> 一键 Tachyon 渲染
  - 支持批量自动渲染和手动预览两种模式
  - 渲染输出文件名与 fchk 一致
  - 多轨道支持：同时显示多个轨道（HOMO+LUMO等），每个轨道独立颜色
  - 氢原子隐藏功能：可选择性隐藏氢原子，突出核心骨架结构
  - 虚线绘制工具：支持手动标注氢键等相互作用

用法：
  直接运行 -> 弹出 GUI
  命令行 -> python fchk_orbital.py folder/ --mo h,l --iso 0.05
  多轨道示例 -> python fchk_orbital.py folder/ --mo h-1,h,l,l+1
"""

import os
import sys
import glob
import subprocess
import threading
import shutil
import time
import tempfile
import socket


# ── 默认路径 ──────────────────────────────────────────────
DEFAULT_MULTIWFN = r"E:\Multiwfn_2026.4.10_bin_Win64\Multiwfn.exe"
DEFAULT_VMD = r"C:\Program Files (x86)\University of Illinois\VMD\vmd.exe"
DEFAULT_TACHYON = r"C:\Program Files (x86)\University of Illinois\VMD\tachyon_WIN32.exe"

# 配置文件路径（与 exe 同目录或脚本同目录）
CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(sys.argv[0] if getattr(sys, 'frozen', False) else __file__)),
    "fchk_orbital.ini"
)


def load_config():
    """从 ini 文件读取路径配置，不存在则返回默认值。"""
    import configparser
    cfg = configparser.ConfigParser()
    paths = {
        "multiwfn": DEFAULT_MULTIWFN,
        "vmd": DEFAULT_VMD,
        "tachyon": DEFAULT_TACHYON,
    }
    if os.path.exists(CONFIG_FILE):
        cfg.read(CONFIG_FILE, encoding="utf-8")
        if "paths" in cfg:
            for k in paths:
                if k in cfg["paths"] and cfg["paths"][k]:
                    paths[k] = cfg["paths"][k]
    return paths


def save_config(multiwfn, vmd, tachyon):
    """保存路径配置到 ini 文件。"""
    import configparser
    cfg = configparser.ConfigParser()
    cfg["paths"] = {
        "multiwfn": multiwfn,
        "vmd": vmd,
        "tachyon": tachyon,
    }
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        cfg.write(f)


# ── vcube2.0 样式定义 ────────────────────────────────────
# 每种样式包含：tachyon_options, 灯光, 阴影/AO, 材质, 颜色, 原子着色
# 所有样式来自 E:\vcube2.0\styles\ (vcube 2.0, 钟诚)

STYLES = {
    "sob_Gold": {
        "desc": "绿蓝, 高光, 棕褐C, Opaque/Glossy (sob原始)",
        "tachyon_options": "-trans_raster3d",
        "lights": {"0": "on", "1": "on", "2": "off", "3": "on"},
        "shadows": "off", "ao": "off",
        "aoambient": "0.8", "aodirect": "0.3",
        # 材质: ambient, diffuse, specular, shininess, mirror, opacity, outline, outlinewidth, transmode
        "surface_mat": [0.1, 0.6, 1.0, 1.0, 0.0, 0.75, 0.0, 0.0, 1.0],
        "surface_mat_b": [0.1, 0.6, 1.0, 1.0, 0.0, 0.75, 0.0, 0.0, 1.0],
        "pos_color": [12, None, None],   # ColorID 12 = green
        "neg_color": [22, None, None],   # ColorID 22 = blue
        "atom_cpk": "0.600000 0.400000 30.000000 30.000000",
        "atom_mat": [0.0, 0.65, 0.5, 0.53, 0.15, 1.0, 2.0, 0.3, 0.0],
        "c_color": "tan", "c_rgb": "0.700000 0.560000 0.360000",
        # 额外 VMD 内置材质属性 (sob 原始: mirror Opaque 0.15, outline Opaque 4.0, outlinewidth Opaque 0.5)
        "extra_mat_lines": [
            "material change mirror Opaque 0.15",
            "material change outline Opaque 4.000000",
            "material change outlinewidth Opaque 0.5",
            "material change ambient Glossy 0.1",
            "material change diffuse Glossy 0.600000",
            "material change opacity Glossy 0.75",
            "material change shininess Glossy 1.0",
        ],
        # 额外显示设置
        "display_distance": "-7.0",
    },
    "sob-art": {
        "desc": "绿蓝, 高光, 经典 (sobereva推荐)",
        "tachyon_options": "-trans_raster3d",
        "lights": {"0": "on", "1": "on", "2": "off", "3": "on"},
        "shadows": "off", "ao": "off",
        "aoambient": "0.8", "aodirect": "0.3",
        # 材质: ambient, diffuse, specular, shininess, mirror, opacity, outline, outlinewidth, transmode
        "surface_mat": [0.1, 0.6, 1.0, 1.0, 0.0, 0.75, 0.0, 0.0, 1.0],
        "surface_mat_b": [0.1, 0.6, 1.0, 1.0, 0.0, 0.75, 0.0, 0.0, 1.0],
        "pos_color": [12, None, None],   # ColorID 12 = green
        "neg_color": [22, None, None],   # ColorID 22 = blue
        "atom_cpk": "0.600000 0.400000 30.000000 30.000000",
        "atom_mat": [0.0, 0.65, 0.5, 0.53, 0.15, 1.0, 2.0, 0.3, 0.0],
        "c_color": "tan", "c_rgb": "0.700000 0.560000 0.360000",
    },
    "ao-shiny": {
        "desc": "橙青, 珠宝感, AO(慢)",
        "tachyon_options": "-trans_raster3d",
        "lights": {"0": "on", "1": "on", "2": "on", "3": "off"},
        "shadows": "on", "ao": "on",
        "aoambient": "0.8", "aodirect": "0.3",
        "surface_mat": [0.20, 0.8, 0.7, 0.3, 0.0, 0.7, 0.0, 0.0, 1.0],
        "surface_mat_b": [0.20, 0.8, 0.7, 0.3, 0.0, 0.7, 0.0, 0.0, 1.0],
        "pos_color": [31, 0.900, 0.500, 0.200],
        "neg_color": [32, 0.000, 0.600, 0.800],
        "atom_cpk": "0.700000 0.350000 30.000000 30.000000",
        "atom_mat": [0.0, 0.85, 0.0, 0.53, 0.0, 1.0, 0.5, 0.9, 0.0],
        "c_color": "gray", "c_rgb": "0.600000 0.600000 0.600000",
    },
    "ao-chalky": {
        "desc": "蓝绿, 粉笔感, AO(慢)",
        "tachyon_options": "-trans_raster3d",
        "lights": {"0": "on", "1": "on", "2": "off", "3": "off"},
        "shadows": "on", "ao": "on",
        "aoambient": "0.8", "aodirect": "0.3",
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
        "aoambient": "0.8", "aodirect": "0.3",
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
        "aoambient": "0.8", "aodirect": "0.3",
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
        "aoambient": "0.8", "aodirect": "0.3",
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
        "aoambient": "0.8", "aodirect": "0.3",
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
        "aoambient": "0.8", "aodirect": "0.3",
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
        "aoambient": "0.8", "aodirect": "0.3",
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
        "aoambient": "0.8", "aodirect": "0.3",
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
        "aoambient": "0.8", "aodirect": "0.3",
        "surface_mat": [0.4, 0.6, 1.0, 0.9, 0.0, 1.0, 0.4, 0.6, 1.0],
        "surface_mat_b": [0.4, 0.6, 1.0, 0.9, 0.0, 1.0, 0.4, 0.6, 1.0],
        "pos_color": [31, 0.850, 0.850, 0.750],
        "neg_color": [32, 0.600, 0.200, 0.300],
        "atom_cpk": "0.600000 0.400000 30.000000 30.000000",
        "atom_mat": [0.1, 0.5, 0.1, 0.3, 0.0, 1.0, 0.5, 0.9, 0.0],
        "c_color": "gray", "c_rgb": "0.600000 0.600000 0.600000",
    },
    # ── IboView 风格光影特效 ──────────────────────────────
    # 基于 IboView 的双指数镜面反射模型
    "iboview-shiny": {
        "desc": "IboView 高光风格, 蓝红配色",
        "tachyon_options": "-trans_raster3d",
        "lights": {"0": "on", "1": "on", "2": "on", "3": "off"},
        "shadows": "off", "ao": "off",
        "aoambient": "0.8", "aodirect": "0.3",
        "surface_mat": [0.15, 0.55, 1.0, 1.0, 0.0, 0.72, 0.0, 0.0, 1.0],
        "surface_mat_b": [0.15, 0.55, 1.0, 1.0, 0.0, 0.72, 0.0, 0.0, 1.0],
        "pos_color": [31, 0.050, 0.350, 0.800],
        "neg_color": [32, 0.900, 0.250, 0.250],
        "atom_cpk": "0.650000 0.400000 30.000000 30.000000",
        "atom_mat": [0.1, 0.65, 0.5, 0.53, 0.20, 1.0, 1.5, 0.3, 0.0],
        "c_color": "tan", "c_rgb": "0.700000 0.560000 0.360000",
        "display_distance": "-7.5",
    },
    "iboview-gold": {
        "desc": "IboView 金色风格, 绿蓝配色",
        "tachyon_options": "-trans_raster3d",
        "lights": {"0": "on", "1": "on", "2": "off", "3": "on"},
        "shadows": "off", "ao": "off",
        "aoambient": "0.8", "aodirect": "0.3",
        "surface_mat": [0.12, 0.60, 1.0, 1.0, 0.0, 0.75, 0.0, 0.0, 1.0],
        "surface_mat_b": [0.12, 0.60, 1.0, 1.0, 0.0, 0.75, 0.0, 0.0, 1.0],
        "pos_color": [12, None, None],
        "neg_color": [22, None, None],
        "atom_cpk": "0.600000 0.400000 30.000000 30.000000",
        "atom_mat": [0.05, 0.70, 0.5, 0.60, 0.18, 1.0, 2.0, 0.3, 0.0],
        "c_color": "tan", "c_rgb": "0.700000 0.560000 0.360000",
        "display_distance": "-7.0",
        "extra_mat_lines": [
            "material change mirror Opaque 0.20",
            "material change outline Opaque 3.5",
            "material change outlinewidth Opaque 0.4",
        ],
    },
    "iboview-crystal": {
        "desc": "IboView 水晶风格, 青粉配色",
        "tachyon_options": "-trans_raster3d",
        "lights": {"0": "on", "1": "on", "2": "on", "3": "on"},
        "shadows": "off", "ao": "off",
        "aoambient": "0.8", "aodirect": "0.3",
        "surface_mat": [0.25, 0.45, 0.95, 0.90, 0.0, 0.65, 0.0, 0.0, 1.0],
        "surface_mat_b": [0.25, 0.45, 0.95, 0.90, 0.0, 0.65, 0.0, 0.0, 1.0],
        "pos_color": [31, 0.100, 0.800, 0.900],
        "neg_color": [32, 0.900, 0.300, 0.600],
        "atom_cpk": "0.700000 0.350000 30.000000 30.000000",
        "atom_mat": [0.15, 0.55, 0.6, 0.70, 0.25, 1.0, 1.0, 0.2, 0.0],
        "c_color": "gray", "c_rgb": "0.650000 0.650000 0.650000",
        "display_distance": "-8.0",
    },
    "iboview-dark": {
        "desc": "IboView 暗黑风格, 紫橙配色",
        "tachyon_options": "-trans_raster3d",
        "lights": {"0": "on", "1": "on", "2": "off", "3": "off"},
        "shadows": "on", "ao": "off",
        "aoambient": "0.85", "aodirect": "0.25",
        "surface_mat": [0.10, 0.50, 0.90, 0.85, 0.0, 0.68, 0.0, 0.0, 1.0],
        "surface_mat_b": [0.10, 0.50, 0.90, 0.85, 0.0, 0.68, 0.0, 0.0, 1.0],
        "pos_color": [31, 0.700, 0.300, 0.800],
        "neg_color": [32, 0.900, 0.600, 0.200],
        "atom_cpk": "0.650000 0.400000 30.000000 30.000000",
        "atom_mat": [0.08, 0.60, 0.5, 0.55, 0.15, 1.0, 1.8, 0.3, 0.0],
        "c_color": "gray", "c_rgb": "0.550000 0.550000 0.550000",
        "display_distance": "-7.5",
    },
    # ── IboView 多轨道配色风格（参考截图）─────────────────────
    "iboview-green-pink": {
        "desc": "IboView 绿粉配色, 经典双色",
        "tachyon_options": "-trans_raster3d",
        "lights": {"0": "on", "1": "on", "2": "on", "3": "off"},
        "shadows": "off", "ao": "off",
        "aoambient": "0.8", "aodirect": "0.3",
        "surface_mat": [0.15, 0.50, 1.0, 1.0, 0.0, 0.70, 0.0, 0.0, 1.0],
        "surface_mat_b": [0.15, 0.50, 1.0, 1.0, 0.0, 0.70, 0.0, 0.0, 1.0],
        "pos_color": [31, 0.250, 0.850, 0.350],
        "neg_color": [32, 0.900, 0.350, 0.550],
        "atom_cpk": "0.600000 0.400000 30.000000 30.000000",
        "atom_mat": [0.12, 0.60, 0.5, 0.55, 0.20, 1.0, 1.5, 0.3, 0.0],
        "c_color": "gray", "c_rgb": "0.750000 0.750000 0.750000",
        "display_distance": "-7.5",
    },
    "iboview-purple-blue": {
        "desc": "IboView 紫蓝配色, 神秘质感",
        "tachyon_options": "-trans_raster3d",
        "lights": {"0": "on", "1": "on", "2": "off", "3": "on"},
        "shadows": "off", "ao": "off",
        "aoambient": "0.8", "aodirect": "0.3",
        "surface_mat": [0.18, 0.48, 1.0, 1.0, 0.0, 0.72, 0.0, 0.0, 1.0],
        "surface_mat_b": [0.18, 0.48, 1.0, 1.0, 0.0, 0.72, 0.0, 0.0, 1.0],
        "pos_color": [31, 0.650, 0.350, 0.850],
        "neg_color": [32, 0.200, 0.450, 0.900],
        "atom_cpk": "0.650000 0.400000 30.000000 30.000000",
        "atom_mat": [0.10, 0.65, 0.5, 0.60, 0.22, 1.0, 1.8, 0.3, 0.0],
        "c_color": "gray", "c_rgb": "0.700000 0.700000 0.700000",
        "display_distance": "-7.5",
    },
    "iboview-cyan-yellow": {
        "desc": "IboView 青黄配色, 明亮对比",
        "tachyon_options": "-trans_raster3d",
        "lights": {"0": "on", "1": "on", "2": "on", "3": "on"},
        "shadows": "off", "ao": "off",
        "aoambient": "0.8", "aodirect": "0.3",
        "surface_mat": [0.20, 0.45, 0.95, 0.95, 0.0, 0.68, 0.0, 0.0, 1.0],
        "surface_mat_b": [0.20, 0.45, 0.95, 0.95, 0.0, 0.68, 0.0, 0.0, 1.0],
        "pos_color": [31, 0.100, 0.850, 0.900],
        "neg_color": [32, 0.950, 0.850, 0.200],
        "atom_cpk": "0.700000 0.350000 30.000000 30.000000",
        "atom_mat": [0.15, 0.55, 0.5, 0.50, 0.18, 1.0, 1.2, 0.3, 0.0],
        "c_color": "gray", "c_rgb": "0.680000 0.680000 0.680000",
        "display_distance": "-8.0",
    },
    "iboview-orange-teal": {
        "desc": "IboView 橙青配色, 温暖对比",
        "tachyon_options": "-trans_raster3d",
        "lights": {"0": "on", "1": "on", "2": "off", "3": "off"},
        "shadows": "off", "ao": "off",
        "aoambient": "0.8", "aodirect": "0.3",
        "surface_mat": [0.12, 0.55, 1.0, 1.0, 0.0, 0.73, 0.0, 0.0, 1.0],
        "surface_mat_b": [0.12, 0.55, 1.0, 1.0, 0.0, 0.73, 0.0, 0.0, 1.0],
        "pos_color": [31, 0.900, 0.500, 0.200],
        "neg_color": [32, 0.150, 0.700, 0.750],
        "atom_cpk": "0.600000 0.400000 30.000000 30.000000",
        "atom_mat": [0.08, 0.68, 0.5, 0.58, 0.25, 1.0, 2.0, 0.3, 0.0],
        "c_color": "tan", "c_rgb": "0.700000 0.560000 0.360000",
        "display_distance": "-7.0",
    },
    "iboview-red-green": {
        "desc": "IboView 红绿配色, 经典互补",
        "tachyon_options": "-trans_raster3d",
        "lights": {"0": "on", "1": "on", "2": "on", "3": "off"},
        "shadows": "off", "ao": "off",
        "aoambient": "0.8", "aodirect": "0.3",
        "surface_mat": [0.10, 0.52, 1.0, 1.0, 0.0, 0.71, 0.0, 0.0, 1.0],
        "surface_mat_b": [0.10, 0.52, 1.0, 1.0, 0.0, 0.71, 0.0, 0.0, 1.0],
        "pos_color": [31, 0.850, 0.200, 0.250],
        "neg_color": [32, 0.200, 0.750, 0.350],
        "atom_cpk": "0.650000 0.400000 30.000000 30.000000",
        "atom_mat": [0.10, 0.62, 0.5, 0.53, 0.20, 1.0, 1.6, 0.3, 0.0],
        "c_color": "gray", "c_rgb": "0.650000 0.650000 0.650000",
        "display_distance": "-7.5",
    },
    "iboview-rainbow": {
        "desc": "IboView 彩虹配色, 多彩效果",
        "tachyon_options": "-trans_raster3d",
        "lights": {"0": "on", "1": "on", "2": "on", "3": "on"},
        "shadows": "off", "ao": "off",
        "aoambient": "0.8", "aodirect": "0.3",
        "surface_mat": [0.18, 0.48, 1.0, 1.0, 0.0, 0.68, 0.0, 0.0, 1.0],
        "surface_mat_b": [0.18, 0.48, 1.0, 1.0, 0.0, 0.68, 0.0, 0.0, 1.0],
        "pos_color": [31, 0.950, 0.150, 0.600],
        "neg_color": [32, 0.150, 0.650, 0.950],
        "atom_cpk": "0.700000 0.350000 30.000000 30.000000",
        "atom_mat": [0.12, 0.60, 0.5, 0.55, 0.22, 1.0, 1.4, 0.3, 0.0],
        "c_color": "white", "c_rgb": "0.850000 0.850000 0.850000",
        "display_distance": "-8.0",
    },
}

# 原子元素着色（所有样式共用，来自 vcube2.0）
ATOM_COLORS = """
color change rgb 101 0.8000 0.8000 0.8000
color change rgb 102 0.8471 1.0000 1.0000
color change rgb 103 0.8000 0.4863 1.0000
color change rgb 104 0.8000 1.0000 0.0000
color change rgb 105 1.0000 0.7098 0.7098
color change rgb 106 0.5569 0.5569 0.5569
color change rgb 107 0.0980 0.0980 0.8980
color change rgb 108 0.8980 0.0000 0.0000
color change rgb 109 0.6980 1.0000 1.0000
color change rgb 110 0.6863 0.8863 0.9569
color change rgb 111 0.6667 0.3569 0.9490
color change rgb 112 0.6980 0.8000 0.0000
color change rgb 113 0.8196 0.6471 0.6471
color change rgb 114 0.4980 0.6000 0.6000
color change rgb 115 1.0000 0.4980 0.0000
color change rgb 116 1.0000 0.7765 0.1569
color change rgb 117 0.0980 0.9373 0.0980
color change rgb 118 0.4980 0.8196 0.8863
color change rgb 119 0.5569 0.2471 0.8275
color change rgb 120 0.6000 0.6000 0.0000
color change rgb 121 0.8980 0.8980 0.8863
color change rgb 122 0.7490 0.7569 0.7765
color change rgb 123 0.6471 0.6471 0.6667
color change rgb 124 0.5373 0.6000 0.7765
color change rgb 125 0.6078 0.4784 0.7765
color change rgb 126 0.4980 0.4784 0.7765
color change rgb 127 0.3569 0.4275 1.0000
color change rgb 128 0.3569 0.4784 0.7569
color change rgb 129 1.0000 0.4784 0.3765
color change rgb 130 0.4863 0.4980 0.6863
color change rgb 131 0.7569 0.5569 0.5569
color change rgb 132 0.4000 0.5569 0.5569
color change rgb 133 0.7373 0.4980 0.8863
color change rgb 134 1.0000 0.6275 0.0000
color change rgb 135 0.6471 0.1294 0.1294
color change rgb 136 0.3569 0.7294 0.8196
color change rgb 137 0.4392 0.1765 0.6863
color change rgb 138 0.4980 0.4000 0.0000
color change rgb 139 0.5765 0.9882 1.0000
color change rgb 140 0.5765 0.8784 0.8784
color change rgb 141 0.4471 0.7569 0.7882
color change rgb 142 0.3294 0.7098 0.7098
color change rgb 143 0.2275 0.6196 0.6588
color change rgb 144 0.1373 0.5569 0.5882
color change rgb 145 0.0392 0.4863 0.5490
color change rgb 146 0.0000 0.4078 0.5176
color change rgb 147 0.6000 0.7765 1.0000
color change rgb 148 1.0000 0.8471 0.5569
color change rgb 149 0.6471 0.4588 0.4471
color change rgb 150 0.4000 0.4980 0.4980
color change rgb 151 0.6196 0.3882 0.7098
color change rgb 152 0.8275 0.4784 0.0000
color change rgb 153 0.5765 0.0000 0.5765
color change rgb 154 0.2588 0.6196 0.6863
color change rgb 155 0.3373 0.0863 0.5569
color change rgb 156 0.4000 0.2000 0.0000
color change rgb 157 0.4392 0.8667 1.0000
color change rgb 158 1.0000 1.0000 0.7765
color change rgb 159 0.8471 1.0000 0.7765
color change rgb 160 0.7765 1.0000 0.7765
color change rgb 161 0.6392 1.0000 0.7765
color change rgb 162 0.5569 1.0000 0.7765
color change rgb 163 0.3765 1.0000 0.7765
color change rgb 164 0.2667 1.0000 0.7765
color change rgb 165 0.1882 1.0000 0.7765
color change rgb 166 0.1176 1.0000 0.7098
color change rgb 167 0.0000 1.0000 0.7098
color change rgb 168 0.0000 0.8980 0.4588
color change rgb 169 0.0000 0.8275 0.3176
color change rgb 170 0.0000 0.7490 0.2196
color change rgb 171 0.0000 0.6667 0.1373
color change rgb 172 0.2980 0.7569 1.0000
color change rgb 173 0.2980 0.6471 1.0000
color change rgb 174 0.1490 0.5765 0.8392
color change rgb 175 0.1490 0.4863 0.6667
color change rgb 176 0.1490 0.4000 0.5882
color change rgb 177 0.0863 0.3294 0.5294
color change rgb 178 0.0863 0.3569 0.5569
color change rgb 179 1.0000 0.8196 0.1373
color change rgb 180 0.7098 0.7098 0.7569
color change rgb 181 0.6471 0.3294 0.2980
color change rgb 182 0.3373 0.3490 0.3765
color change rgb 183 0.6196 0.3098 0.7098
color change rgb 184 0.6667 0.3569 0.0000
color change rgb 185 0.4588 0.3098 0.2667
color change rgb 186 0.2588 0.5098 0.5882
color change rgb 187 0.2588 0.0000 0.4000
color change rgb 188 0.2980 0.0980 0.0000
color change rgb 189 0.4392 0.6667 0.9765
color change rgb 190 0.0000 0.7294 1.0000
color change rgb 191 0.0000 0.6275 1.0000
color change rgb 192 0.0000 0.5569 1.0000
color change rgb 193 0.0000 0.4980 0.9490
color change rgb 194 0.0000 0.4196 0.9490
color change rgb 195 0.3294 0.3569 0.9490
color change rgb 196 0.4667 0.3569 0.8863
color change rgb 197 0.5373 0.3686 0.8863
color change rgb 198 0.6275 0.2078 0.8275
color change rgb 199 0.6588 0.1686 0.7765
color change rgb 200 0.6980 0.1176 0.7294
color change rgb 201 0.6980 0.0471 0.6471
color change rgb 202 0.7373 0.0471 0.5294
color change rgb 203 0.7765 0.0000 0.4000
color change rgb 204 1.0000 0.4980 0.4980
color change rgb 205 0.8980 0.4000 0.4000
color change rgb 206 0.8000 0.2980 0.2980
color change rgb 207 0.6980 0.2000 0.2000
color change rgb 208 0.6000 0.0980 0.0980
color change rgb 209 0.5490 0.0000 0.0000
color change rgb 210 0.4980 0.0000 0.0000
color change rgb 211 0.4471 0.0000 0.0000
color Element H  101
color Element He 102
color Element Li 103
color Element Be 104
color Element B  105
color Element C  106
color Element N  107
color Element O  108
color Element F  109
color Element Ne 110
color Element Na 111
color Element Mg 112
color Element Al 113
color Element Si 114
color Element P  115
color Element S  116
color Element Cl 117
color Element Ar 118
color Element K  119
color Element Ca 120
color Element Sc 121
color Element Ti 122
color Element V  123
color Element Cr 124
color Element Mn 125
color Element Fe 126
color Element Co 127
color Element Ni 128
color Element Cu 129
color Element Zn 130
color Element Ga 131
color Element Ge 132
color Element As 133
color Element Se 134
color Element Br 135
color Element Kr 136
color Element Rb 137
color Element Sr 138
color Element Y  139
color Element Zr 140
color Element Nb 141
color Element Mo 142
color Element Tc 143
color Element Ru 144
color Element Rh 145
color Element Pd 146
color Element Ag 147
color Element Cd 148
color Element In 149
color Element Sn 150
color Element Sb 151
color Element Te 152
color Element I  153
color Element Xe 154
color Element Cs 155
color Element Ba 156
color Element La 157
color Element Ce 158
color Element Pr 159
color Element Nd 160
color Element Pm 161
color Element Sm 162
color Element Eu 163
color Element Gd 164
color Element Tb 165
color Element Dy 166
color Element Ho 167
color Element Er 168
color Element Tm 169
color Element Yb 170
color Element Lu 171
color Element Hf 172
color Element Ta 173
color Element W  174
color Element Re 175
color Element Os 176
color Element Ir 177
color Element Pt 178
color Element Au 179
color Element Hg 180
color Element Tl 181
color Element Pb 182
color Element Bi 183
color Element Po 184
color Element At 185
color Element Rn 186
color Element Fr 187
color Element Ra 188
color Element Ac 189
color Element Th 190
color Element Pa 191
color Element U  192
color Element Np 193
color Element Pu 194
color Element Am 195
color Element Cm 196
color Element Bk 197
color Element Cf 198
color Element Es 199
color Element Fm 200
color Element Md 201
color Element No 202
color Element Lr 203
color Element Rf 204
color Element Db 205
color Element Sg 206
color Element Bh 207
color Element Hs 208
color Element Mt 209
color Element Ds 210
color Element Rg 211
"""

# ── 多轨道颜色方案 ────────────────────────────────────────
MULTI_ORBIT_COLORS = [
    {"pos": [12, None, None, None], "neg": [22, None, None, None]},
    {"pos": [31, 0.900, 0.500, 0.200], "neg": [32, 0.000, 0.600, 0.800]},
    {"pos": [33, 0.800, 0.200, 0.200], "neg": [34, 0.600, 0.200, 0.600]},
    {"pos": [35, 0.900, 0.700, 0.100], "neg": [36, 0.900, 0.300, 0.600]},
    {"pos": [37, 0.200, 0.700, 0.700], "neg": [38, 0.700, 0.500, 0.200]},
    {"pos": [39, 0.600, 0.400, 0.800], "neg": [40, 0.300, 0.700, 0.400]},
]


def _gen_multi_orbital_tcl(cube_files, isovalues, base_style_name, shade_mode="full",
                           keep_h_indices=None):
    """生成多轨道 VMD TCL 脚本
    cube_files: [(cube_path, orbital_name), ...]
    isovalues: [isovalue, ...] 或单个值应用于所有
    keep_h_indices: 要保留的氢原子序号列表（从0开始），None=保留所有，[]=删除所有
    """
    if not cube_files:
        return ""

    s = STYLES.get(base_style_name, STYLES["sob-art"])

    light_lines = ""
    for k, v in s["lights"].items():
        light_lines += f"light {k} {v}\n"

    if shade_mode == "medium":
        shadow_on = True
        ao_on = False
    else:
        shadow_on = s["shadows"] == "on"
        ao_on = s["ao"] == "on"

    shadow_lines = f"display shadows {'on' if shadow_on else 'off'}\n"
    if ao_on:
        shadow_lines += "display ambientocclusion on\n"
    else:
        shadow_lines += "display ambientocclusion off\n"
    shadow_lines += f"display aoambient {s.get('aoambient', '0.8')}\ndisplay aodirect {s.get('aodirect', '0.3')}\n"

    # Bug fix: mat_names 必须包含 transmode（与 atom_mat 的 9 个元素对应）
    mat_names = ["ambient", "diffuse", "specular", "shininess", "mirror", "opacity", "outline", "outlinewidth", "transmode"]
    atom_mat_lines = "if {[lsearch [material list] _stl_atom] < 0} {material add _stl_atom}\n"
    for name, val in zip(mat_names, s["atom_mat"]):
        atom_mat_lines += f"material change {name} _stl_atom {val}\n"

    if isinstance(isovalues, (int, float)):
        isovalues = [isovalues] * len(cube_files)

    # 构造氢原子过滤 TCL（用 modselect 控制，不影响等值面）
    if keep_h_indices is not None:
        if keep_h_indices:
            h_idx_list = " ".join(map(str, keep_h_indices))
            h_sel_str = f"not element H or (element H and index {h_idx_list})"
        else:
            h_sel_str = "not element H"
        h_filter_template = f"""
# 隐藏氢原子（只影响 rep 0 原子球棍）
mol modselect 0 top "{h_sel_str}"
"""
    else:
        h_filter_template = ""

    orbital_reps = ""
    for idx, (cube_path, orb_name) in enumerate(cube_files):
        cube_name = os.path.basename(cube_path)
        iso = isovalues[idx] if idx < len(isovalues) else isovalues[-1]
        # Bug fix: 每个轨道使用对应颜色方案，而非固定用 MULTI_ORBIT_COLORS[0]
        colors = MULTI_ORBIT_COLORS[idx % len(MULTI_ORBIT_COLORS)]

        mat_name_a = f"_stl_orb_{idx}_a"
        mat_name_b = f"_stl_orb_{idx}_b"

        mat_a_lines = f"if {{[lsearch [material list] {mat_name_a}] < 0}} {{material add {mat_name_a}}}\n"
        for name, val in zip(mat_names, s["surface_mat"]):
            mat_a_lines += f"material change {name} {mat_name_a} {val}\n"

        mat_b_lines = f"if {{[lsearch [material list] {mat_name_b}] < 0}} {{material add {mat_name_b}}}\n"
        for name, val in zip(mat_names, s["surface_mat_b"]):
            mat_b_lines += f"material change {name} {mat_name_b} {val}\n"

        pc = colors["pos"]
        if len(pc) == 4 and pc[1] is not None:
            color_pos = f"mol modcolor 1 top ColorID {pc[0]}\ncolor change rgb {pc[0]} {pc[1]} {pc[2]} {pc[3]}"
        else:
            color_pos = f"mol modcolor 1 top ColorID {pc[0]}"

        nc = colors["neg"]
        if len(nc) == 4 and nc[1] is not None:
            color_neg = f"mol modcolor 2 top ColorID {nc[0]}\ncolor change rgb {nc[0]} {nc[1]} {nc[2]} {nc[3]}"
        else:
            color_neg = f"mol modcolor 2 top ColorID {nc[0]}"

        # 每个轨道都需要执行氢原子过滤（每个 cube 是独立分子）
        h_filter_code = h_filter_template

        orbital_reps += f"""
# 轨道 {idx + 1}: {orb_name} ({cube_name})
mol new {cube_name} type cube first 0 last 0 step 1 waitfor all
# 原子
mol modstyle 0 top CPK {s['atom_cpk']}
mol modmaterial 0 top _stl_atom
{atom_mat_lines}
mol modcolor 0 top Element
{ATOM_COLORS}
color Element C {s['c_color']}
color change rgb {s['c_color']} {s['c_rgb']}
{h_filter_code}
# 正等值面
mol addrep top
mol modstyle 1 top Isosurface {iso} 0 0 0 1 1
{color_pos}
{mat_a_lines}
mol modmaterial 1 top {mat_name_a}
# 负等值面
mol addrep top
mol modstyle 2 top Isosurface -{iso} 0 0 0 1 1
{color_neg}
{mat_b_lines}
mol modmaterial 2 top {mat_name_b}
"""

    # 额外 VMD 内置材质/显示设置
    extra_lines = s.get("extra_mat_lines", [])
    extra_mat_tcl = "\n".join(extra_lines) + "\n" if extra_lines else ""

    return f"""color Display Background white
axes location Off
display depthcue off
display projection Orthographic
display rendermode GLSL

{light_lines}
{shadow_lines}

# 多轨道等值面
{orbital_reps}

display distance {s.get('display_distance', '-8.0')}
display height 10
{extra_mat_tcl}
"""


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


def _style_tcl(cube_name, isovalue, style_name, shade_mode="full", keep_h_indices=None):
    """根据样式名生成 VMD TCL 设置脚本（不含 socket 服务器和 render 命令）。
    shade_mode: 'full'=全阴影, 'medium'=中等阴影, 'noshadow'=无阴影
    keep_h_indices: 要保留的氢原子序号列表（从0开始），None=保留所有，[]=删除所有
    """
    s = STYLES.get(style_name, STYLES["sob-art"])

    # 灯光
    light_lines = ""
    for k, v in s["lights"].items():
        light_lines += f"light {k} {v}\n"

    # 阴影/AO：shade_mode 覆盖样式默认值
    if shade_mode == "medium":
        shadow_on = True
        ao_on = False
    else:  # full
        shadow_on = s["shadows"] == "on"
        ao_on = s["ao"] == "on"
    shadow_lines = f"display shadows {'on' if shadow_on else 'off'}\n"
    if ao_on:
        shadow_lines += "display ambientocclusion on\n"
    else:
        shadow_lines += "display ambientocclusion off\n"
    shadow_lines += "display aoambient 0.8\ndisplay aodirect 0.3\n"

    # Bug fix: mat_names 包含 transmode（9项），与 surface_mat / atom_mat 对齐
    mat_names = ["ambient", "diffuse", "specular", "shininess", "mirror", "opacity", "outline", "outlinewidth", "transmode"]

    # 表面材质
    mat_a_lines = "if {[lsearch [material list] _stl_a] < 0} {material add _stl_a}\n"
    for name, val in zip(mat_names, s["surface_mat"]):
        mat_a_lines += f"material change {name} _stl_a {val}\n"

    mat_b_lines = "if {[lsearch [material list] _stl_b] < 0} {material add _stl_b}\n"
    for name, val in zip(mat_names, s["surface_mat_b"]):
        mat_b_lines += f"material change {name} _stl_b {val}\n"

    # 原子材质
    atom_mat_lines = "if {[lsearch [material list] _stl_atom] < 0} {material add _stl_atom}\n"
    for name, val in zip(mat_names, s["atom_mat"]):
        atom_mat_lines += f"material change {name} _stl_atom {val}\n"

    # 表面颜色
    pc = s["pos_color"]
    if len(pc) == 4:  # ColorID + RGB
        color_pos = f"mol modcolor 1 top ColorID {pc[0]}\ncolor change rgb {pc[0]} {pc[1]} {pc[2]} {pc[3]}"
    else:
        color_pos = f"mol modcolor 1 top ColorID {pc[0]}"

    nc = s["neg_color"]
    if len(nc) == 4:
        color_neg = f"mol modcolor 2 top ColorID {nc[0]}\ncolor change rgb {nc[0]} {nc[1]} {nc[2]} {nc[3]}"
    else:
        color_neg = f"mol modcolor 2 top ColorID {nc[0]}"

    # 隐藏氢原子 TCL（用 modselect 控制 rep 0 的原子选择，不影响等值面 rep 1/2）
    if keep_h_indices is not None:
        if keep_h_indices:
            h_idx_list = " ".join(map(str, keep_h_indices))
            h_sel_str = f"not element H or (element H and index {h_idx_list})"
        else:
            h_sel_str = "not element H"
        h_filter_code = f"""
# 隐藏氢原子（只影响原子球棍 rep 0，不影响等值面 rep 1/2）
mol modselect 0 top "{h_sel_str}"
"""
    else:
        h_filter_code = ""

    # 额外 VMD 内置材质/显示设置（sob_Gold 等样式使用 Opaque/Glossy 原始材质）
    extra_lines = s.get("extra_mat_lines", [])
    extra_mat_tcl = "\n".join(extra_lines) + "\n" if extra_lines else ""

    return f"""color Display Background white
axes location Off
display depthcue off
display projection Orthographic
display rendermode GLSL

{light_lines}
{shadow_lines}

mol new {cube_name} type cube first 0 last 0 step 1 waitfor all

# 原子
mol modstyle 0 top CPK {s['atom_cpk']}
mol modmaterial 0 top _stl_atom
{atom_mat_lines}
mol modcolor 0 top Element
{ATOM_COLORS}
color Element C {s['c_color']}
color change rgb {s['c_color']} {s['c_rgb']}

# 正等值面
mol addrep top
mol modstyle 1 top Isosurface {isovalue} 0 0 0 1 1
{color_pos}
{mat_a_lines}
mol modmaterial 1 top _stl_a

# 负等值面
mol addrep top
mol modstyle 2 top Isosurface -{isovalue} 0 0 0 1 1
{color_neg}
{mat_b_lines}
mol modmaterial 2 top _stl_b

display distance {s.get('display_distance', '-8.0')}
display height 10
{extra_mat_tcl}
{h_filter_code}
"""


# ── Multiwfn：单个 fchk -> cube ──────────────────────────
def gen_cube(fchk_path, orbital="h", grid_quality=2,
             multiwfn_exe=None, work_dir=None):
    """调用 Multiwfn 生成轨道波函数 cube 文件。"""
    if multiwfn_exe is None:
        multiwfn_exe = DEFAULT_MULTIWFN
    if work_dir is None:
        work_dir = os.path.dirname(os.path.abspath(fchk_path))
    os.makedirs(work_dir, exist_ok=True)

    fchk_name = os.path.basename(fchk_path)
    ascii_dir = os.path.join(work_dir, "_multiwfn_tmp")
    os.makedirs(ascii_dir, exist_ok=True)
    ascii_fchk = os.path.join(ascii_dir, fchk_name)
    if not os.path.exists(ascii_fchk):
        shutil.copy2(fchk_path, ascii_fchk)

    inputs = (
        "\n" + fchk_name + "\n5\n4\n" + orbital + "\n"
        + str(grid_quality) + "\n2\n0\nq\n"
    )

    try:
        subprocess.run(
            multiwfn_exe, input=inputs, capture_output=True,
            cwd=ascii_dir, timeout=600, encoding="utf-8", errors="replace",
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"  错误: {e}")
        return None

    cube_src = os.path.join(ascii_dir, "MOvalue.cub")
    if not os.path.exists(cube_src):
        return None

    stem = os.path.splitext(fchk_name)[0]
    cube_dst = os.path.join(work_dir, f"{stem}_MO{orbital}.cub")
    shutil.move(cube_src, cube_dst)
    try:
        shutil.rmtree(ascii_dir)
    except OSError:
        pass
    return cube_dst


# ── Multiwfn：多轨道 -> 多个 cube ───────────────────────
def gen_multi_cubes(fchk_path, orbitals, grid_quality=2,
                    multiwfn_exe=None, work_dir=None):
    """
    调用 Multiwfn 生成多个轨道波函数 cube 文件。
    orbitals: 轨道列表，如 ['h', 'l', 'h-1', 'l+1'] 或 ['5', '6', '7', '8']
    返回: [(cube_path, orbital_name), ...] 或 None
    """
    if multiwfn_exe is None:
        multiwfn_exe = DEFAULT_MULTIWFN
    if work_dir is None:
        work_dir = os.path.dirname(os.path.abspath(fchk_path))
    os.makedirs(work_dir, exist_ok=True)

    fchk_name = os.path.basename(fchk_path)
    stem = os.path.splitext(fchk_name)[0]
    results = []

    for orbital in orbitals:
        cube_name = f"{stem}_MO{orbital}.cub"
        cube_path = os.path.join(work_dir, cube_name)

        if os.path.exists(cube_path):
            results.append((cube_path, orbital))
            continue

        ascii_dir = os.path.join(work_dir, f"_multiwfn_tmp_{orbital}")
        os.makedirs(ascii_dir, exist_ok=True)
        ascii_fchk = os.path.join(ascii_dir, fchk_name)
        if not os.path.exists(ascii_fchk):
            shutil.copy2(fchk_path, ascii_fchk)

        inputs = (
            "\n" + fchk_name + "\n5\n4\n" + str(orbital) + "\n"
            + str(grid_quality) + "\n2\n0\nq\n"
        )

        try:
            subprocess.run(
                multiwfn_exe, input=inputs, capture_output=True,
                cwd=ascii_dir, timeout=600, encoding="utf-8", errors="replace",
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"  错误: {e}")
            continue

        cube_src = os.path.join(ascii_dir, "MOvalue.cub")
        if os.path.exists(cube_src):
            shutil.move(cube_src, cube_path)
            results.append((cube_path, orbital))

        try:
            shutil.rmtree(ascii_dir)
        except OSError:
            pass

    return results if results else None


# ── VMD 预览：打开 GUI 窗口 + socket 服务器 ──────────────
def preview_cube(cube_path, isovalue=0.05, style_name="sob-art", vmd_exe=None,
                 shade_mode="full", keep_h_indices=None):
    """
    打开 VMD GUI 窗口预览 cube 文件，并启动 socket 服务器等待渲染命令。
    keep_h_indices: 要保留的氢原子序号列表，None=保留所有，[]=删除所有
    返回: (port, render_dir) 或 (None, None)
    """
    if vmd_exe is None:
        vmd_exe = DEFAULT_VMD
    cube_name = os.path.basename(cube_path)
    work_dir = os.path.dirname(os.path.abspath(cube_path))

    # 检测中文路径
    try:
        cube_path.encode("ascii")
        has_nonascii = False
    except UnicodeEncodeError:
        has_nonascii = True

    if has_nonascii:
        render_dir = tempfile.mkdtemp(prefix="vmd_")
        tmp_cube = os.path.join(render_dir, cube_name)
        shutil.copy2(cube_path, tmp_cube)
    else:
        render_dir = work_dir

    # 找一个空闲端口
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    # 样式 TCL + socket 服务器
    style_tcl = _style_tcl(cube_name, isovalue, style_name, shade_mode=shade_mode,
                            keep_h_indices=keep_h_indices)
    socket_tcl = f"""
# === Socket 服务器：等待 Python 端发送命令 ===
set serverSocket [socket -server _vmd_accept -myaddr 127.0.0.1 {port}]
proc _vmd_accept {{chan addr port}} {{
    global _vmd_waiting
    fconfigure $chan -buffering line -translation binary
    fileevent $chan readable [list _vmd_handle $chan]
}}

proc _vmd_handle {{chan}} {{
    if [eof $chan] {{
        close $chan
        return
    }}
    gets $chan cmd
    if {{$cmd eq ""}} return

    if [catch {{uplevel #0 $cmd}} err] {{
        puts $chan "ERROR: $err"
    }} else {{
        puts $chan "OK"
    }}
    flush $chan
}}

puts "==========================================="
puts " VMD 预览已就绪 (样式: {style_name})"
puts " 在 Python GUI 中点击 [渲染当前视角] 按钮"
puts " 端口: {port}"
puts "==========================================="
"""
    tcl = _draw_bond_tcl() + style_tcl + socket_tcl
    tcl_path = os.path.join(render_dir, "_preview.tcl")
    with open(tcl_path, "w") as f:
        f.write(tcl)

    subprocess.Popen(
        [vmd_exe, "-e", "_preview.tcl"],
        cwd=render_dir,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )

    return port, render_dir


# ── VMD 多轨道预览 ──────────────────────────────────────
def preview_multi_cubes(cube_files, isovalues, style_name="sob-art",
                        vmd_exe=None, shade_mode="full", keep_h_indices=None):
    """
    打开 VMD GUI 窗口预览多个 cube 文件，并启动 socket 服务器等待渲染命令。
    cube_files: [(cube_path, orbital_name), ...]
    isovalues: [isovalue, ...] 或单个值应用于所有
    keep_h_indices: 要保留的氢原子序号列表，None=保留所有，[]=删除所有
    返回: (port, render_dir, copied_cubes) 或 (None, None, None)
    """
    if vmd_exe is None:
        vmd_exe = DEFAULT_VMD

    if not cube_files:
        return None, None, None

    work_dir = os.path.dirname(os.path.abspath(cube_files[0][0]))
    has_nonascii = False
    for cube_path, _ in cube_files:
        try:
            cube_path.encode("ascii")
        except UnicodeEncodeError:
            has_nonascii = True
            break

    if has_nonascii:
        render_dir = tempfile.mkdtemp(prefix="vmd_multi_")
        copied_cubes = []
        for cube_path, orb_name in cube_files:
            cube_name = os.path.basename(cube_path)
            tmp_cube = os.path.join(render_dir, cube_name)
            shutil.copy2(cube_path, tmp_cube)
            copied_cubes.append((tmp_cube, orb_name))
    else:
        render_dir = work_dir
        copied_cubes = cube_files

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    style_tcl = _gen_multi_orbital_tcl(copied_cubes, isovalues, style_name, shade_mode=shade_mode,
                                       keep_h_indices=keep_h_indices)
    orb_names = ", ".join([orb for _, orb in copied_cubes])
    socket_tcl = f"""
# === Socket 服务器：等待 Python 端发送命令 ===
set serverSocket [socket -server _vmd_accept -myaddr 127.0.0.1 {port}]
proc _vmd_accept {{chan addr port}} {{
    global _vmd_waiting
    fconfigure $chan -buffering line -translation binary
    fileevent $chan readable [list _vmd_handle $chan]
}}

proc _vmd_handle {{chan}} {{
    if [eof $chan] {{
        close $chan
        return
    }}
    gets $chan cmd
    if {{$cmd eq ""}} return

    if [catch {{uplevel #0 $cmd}} err] {{
        puts $chan "ERROR: $err"
    }} else {{
        puts $chan "OK"
    }}
    flush $chan
}}

puts "==========================================="
puts " VMD 多轨道预览已就绪"
puts " 轨道: {orb_names}"
puts " 样式: {style_name}"
puts " 在 Python GUI 中点击 [渲染当前视角] 按钮"
puts " 端口: {port}"
puts "==========================================="
"""
    tcl = _draw_bond_tcl() + style_tcl + socket_tcl
    tcl_path = os.path.join(render_dir, "_preview_multi.tcl")
    with open(tcl_path, "w") as f:
        f.write(tcl)

    subprocess.Popen(
        [vmd_exe, "-e", "_preview_multi.tcl"],
        cwd=render_dir,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )

    return port, render_dir, copied_cubes


# ── 通过 socket 发送渲染命令到 VMD ─────────────────────
def render_current_view(port, render_dir, output_png=None,
                        tachyon_exe=None, resolution=(2000, 1500),
                        style_name="sob-art", shade_mode="full",
                        trans_raster=True, threads=4):
    """
    连接到 VMD 的 socket 服务器，发送 render Tachyon 命令，
    然后用 Tachyon 渲染成 PNG。
    
    参数:
        trans_raster: 是否启用 -trans_raster3d 选项
        threads: Tachyon 渲染线程数
    """
    if tachyon_exe is None:
        tachyon_exe = DEFAULT_TACHYON
    s = STYLES.get(style_name, STYLES["sob-art"])

    # 连接 VMD socket
    vmd_sock = None
    last_error = None
    for attempt in range(10):
        try:
            vmd_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            vmd_sock.settimeout(3)
            vmd_sock.connect(("127.0.0.1", port))
            break
        except (ConnectionRefusedError, socket.timeout, OSError) as e:
            last_error = str(e)
            time.sleep(0.5)
            if vmd_sock:
                vmd_sock.close()
            vmd_sock = None

    if vmd_sock is None:
        print(f"  无法连接 VMD (端口 {port}): {last_error}")
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

    # 清理旧文件
    for fn in ["vmdscene.dat", "_render.bmp"]:
        fp = os.path.join(render_dir, fn)
        if os.path.exists(fp):
            os.remove(fp)

    resp = send_cmd("render Tachyon vmdscene.dat")
    vmd_sock.close()

    dat = os.path.join(render_dir, "vmdscene.dat")
    if not os.path.exists(dat):
        print(f"  vmdscene.dat 不存在: {dat}")
        return None

    # Tachyon 渲染：shade_mode 决定光影级别
    shade_flag = "-fullshade" if shade_mode == "full" else "-mediumshade"
    bmp_name = "_render.bmp"
    args = [
        tachyon_exe, "vmdscene.dat",
        "-format", "BMP", "-o", bmp_name,
        "-res", str(resolution[0]), str(resolution[1]),
        "-numthreads", str(threads), "-aasamples", "24",
        shade_flag,
    ]
    # 根据用户选择决定是否添加 -trans_raster3d
    if trans_raster and s["tachyon_options"]:
        extra = s["tachyon_options"].split()
        args.extend(extra)

    try:
        result = subprocess.run(
            args, capture_output=True, cwd=render_dir, timeout=600,
            encoding="utf-8", errors="replace",
        )
        if result.returncode != 0:
            print(f"  Tachyon 执行失败 (返回码: {result.returncode})")
            print(f"  命令: {' '.join(args)}")
            if result.stderr:
                print(f"  错误输出: {result.stderr[:500]}")
            return None
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"  Tachyon 执行异常: {e}")
        return None

    bmp = os.path.join(render_dir, bmp_name)
    if not os.path.exists(bmp):
        print(f"  BMP 文件不存在: {bmp}")
        return None

    if output_png is None:
        output_png = os.path.join(render_dir, "render.png")

    try:
        from PIL import Image
        img = Image.open(bmp)
        img.save(output_png)
    except ImportError:
        output_png = bmp

    return output_png


# ── 自动渲染（无预览，批量模式用）─────────────────────────
def render_cube_auto(cube_path, output_png=None, isovalue=0.05,
                     vmd_exe=None, tachyon_exe=None,
                     resolution=(2000, 1500), style_name="sob-art", shade_mode="full"):
    """自动渲染（不打开 VMD GUI），用于批量模式。"""
    if vmd_exe is None:
        vmd_exe = DEFAULT_VMD
    if tachyon_exe is None:
        tachyon_exe = DEFAULT_TACHYON
    if output_png is None:
        output_png = os.path.splitext(cube_path)[0] + ".png"

    cube_name = os.path.basename(cube_path)
    work_dir = os.path.dirname(os.path.abspath(cube_path))

    try:
        cube_path.encode("ascii")
        has_nonascii = False
    except UnicodeEncodeError:
        has_nonascii = True

    if has_nonascii:
        tmp_dir = tempfile.mkdtemp(prefix="vmd_")
        tmp_cube = os.path.join(tmp_dir, cube_name)
        shutil.copy2(cube_path, tmp_cube)
        render_dir = tmp_dir
    else:
        render_dir = work_dir

    s = STYLES.get(style_name, STYLES["sob-art"])
    style_tcl = _style_tcl(cube_name, isovalue, style_name, shade_mode=shade_mode)
    tcl = style_tcl + "render Tachyon vmdscene.dat\nquit\n"

    tcl_path = os.path.join(render_dir, "_auto_render.tcl")
    with open(tcl_path, "w") as f:
        f.write(tcl)

    for fn in ["vmdscene.dat"]:
        fp = os.path.join(render_dir, fn)
        if os.path.exists(fp):
            os.remove(fp)

    try:
        subprocess.run(
            [vmd_exe, "-dispdev", "text", "-e", "_auto_render.tcl"],
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
        if has_nonascii:
            dst = os.path.splitext(cube_path)[0] + ".bmp"
            shutil.copy2(bmp, dst)
            output_png = dst

    for fn in ["vmdscene.dat", "_auto_render.tcl", bmp_name]:
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
            self.root.title("轨道等值面可视化 v5 — Multiwfn + VMD/Tachyon (多轨道支持)")
            self.root.geometry("820x850")
            self.running = False

            self.vmd_port = None
            self.vmd_render_dir = None
            self.vmd_process = None
            self.vmd_cube_path = None
            self.vmd_multi_cubes = None

            # ── 路径设置 ──
            frm0 = ttk.LabelFrame(root, text="软件路径")
            frm0.pack(fill="x", padx=10, pady=(5, 2))

            r_paths = ttk.Frame(frm0); r_paths.pack(fill="x", padx=5, pady=2)
            ttk.Label(r_paths, text="Multiwfn:").pack(side="left")
            self.var_mw = tk.StringVar(value=paths["multiwfn"])
            ttk.Entry(r_paths, textvariable=self.var_mw, width=52).pack(
                side="left", fill="x", expand=True, padx=3)
            ttk.Button(r_paths, text="浏览", width=5,
                       command=lambda: self._browse_exe("multiwfn")).pack(side="left")

            r_paths2 = ttk.Frame(frm0); r_paths2.pack(fill="x", padx=5, pady=2)
            ttk.Label(r_paths2, text="VMD:").pack(side="left")
            self.var_vmd = tk.StringVar(value=paths["vmd"])
            ttk.Entry(r_paths2, textvariable=self.var_vmd, width=52).pack(
                side="left", fill="x", expand=True, padx=3)
            ttk.Button(r_paths2, text="浏览", width=5,
                       command=lambda: self._browse_exe("vmd")).pack(side="left")

            # ── 文件选择 ──
            frm1 = ttk.LabelFrame(root, text="输入")
            frm1.pack(fill="x", padx=10, pady=5)

            self.var_mode = tk.StringVar(value="file")
            ttk.Radiobutton(frm1, text="文件夹", variable=self.var_mode,
                            value="folder").pack(side="left", padx=5)
            ttk.Radiobutton(frm1, text="单文件", variable=self.var_mode,
                            value="file").pack(side="left", padx=5)

            self.var_path = tk.StringVar()
            ttk.Entry(frm1, textvariable=self.var_path, width=55).pack(
                side="left", fill="x", expand=True, padx=5, pady=5)
            ttk.Button(frm1, text="浏览", command=self._browse).pack(
                side="right", padx=5, pady=5)

            # ── 参数 ──
            frm2 = ttk.LabelFrame(root, text="参数")
            frm2.pack(fill="x", padx=10, pady=5)

            r1 = ttk.Frame(frm2); r1.pack(fill="x", padx=5, pady=2)
            ttk.Label(r1, text="轨道编号:").pack(side="left")
            self.var_orbital = tk.StringVar(value="h")
            orb_entry = ttk.Entry(r1, textvariable=self.var_orbital, width=25)
            orb_entry.pack(side="left", padx=5)
            ttk.Label(r1, text="(逗号分隔，如: h,l,h-1,l+1)").pack(side="left")
            ttk.Label(r1, text="  等值面:").pack(side="left")
            self.var_iso = tk.StringVar(value="0.05")
            ttk.Entry(r1, textvariable=self.var_iso, width=7).pack(side="left", padx=5)

            r1b = ttk.Frame(frm2); r1b.pack(fill="x", padx=5, pady=2)
            ttk.Label(r1b, text="快捷:").pack(side="left")
            for txt, val in [
                ("H", "h"), ("L", "l"),
                ("H-1", "h-1"), ("L+1", "l+1"),
                ("H-2", "h-2"), ("L+2", "l+2"),
            ]:
                ttk.Button(r1b, text=txt, width=4,
                          command=lambda v=val: self._add_orbital(v)
                          ).pack(side="left", padx=1)
            ttk.Button(r1b, text="H+L", width=5,
                      command=lambda: self.var_orbital.set("h,l")).pack(side="left", padx=(10, 1))
            ttk.Button(r1b, text="H-1+H+L+L+1", width=12,
                      command=lambda: self.var_orbital.set("h-1,h,l,l+1")).pack(side="left", padx=1)
            ttk.Button(r1b, text="H-2+H-1+H+L+L+1+L+2", width=18,
                      command=lambda: self.var_orbital.set("h-2,h-1,h,l,l+1,l+2")).pack(side="left", padx=1)
            ttk.Label(r1b, text="  网格:").pack(side="left", padx=(10, 0))
            self.var_grid = tk.StringVar(value="2")
            ttk.Combobox(r1b, textvariable=self.var_grid, width=3,
                         values=["1", "2", "3"], state="readonly"
                         ).pack(side="left", padx=5)
            ttk.Label(r1b, text="(1低 2中 3高)").pack(side="left")

            r_style = ttk.Frame(frm2); r_style.pack(fill="x", padx=5, pady=2)
            ttk.Label(r_style, text="样式:").pack(side="left")
            # 构建样式列表：显示 "名称 - 描述"
            style_names = list(STYLES.keys())
            style_display = [f"{n}  ({STYLES[n]['desc']})" for n in style_names]
            self.var_style = tk.StringVar(value=style_display[0])
            self.style_combo = ttk.Combobox(r_style, textvariable=self.var_style,
                                            width=40, values=style_display, state="readonly")
            self.style_combo.pack(side="left", padx=5)
            # 默认选中 sob-art
            self.style_combo.current(0)

            r2 = ttk.Frame(frm2); r2.pack(fill="x", padx=5, pady=2)
            ttk.Label(r2, text="分辨率:").pack(side="left")
            self.var_res = tk.StringVar(value="2000x1500")
            ttk.Combobox(r2, textvariable=self.var_res, width=12,
                         values=["2000x1500", "1200x900", "3000x2250"],
                         state="readonly"
                         ).pack(side="left", padx=5)
            self.var_shade = tk.StringVar(value="full")
            ttk.Label(r2, text="光影:").pack(side="left", padx=(20, 0))
            for text, val in [("Full", "full"), ("Medium", "medium")]:
                ttk.Radiobutton(r2, text=text, variable=self.var_shade,
                                value=val).pack(side="left", padx=3)

            # 模式选择
            r3 = ttk.Frame(frm2); r3.pack(fill="x", padx=5, pady=2)
            self.var_auto = tk.BooleanVar(value=False)
            ttk.Checkbutton(r3, text="自动渲染（不预览，批量模式）",
                            variable=self.var_auto).pack(side="left")
            self.var_open = tk.BooleanVar(value=False)
            ttk.Checkbutton(r3, text="完成后打开文件夹",
                            variable=self.var_open).pack(side="left", padx=20)

            # Tachyon 参数
            r4 = ttk.Frame(frm2); r4.pack(fill="x", padx=5, pady=2)
            self.var_trans_raster = tk.BooleanVar(value=True)
            ttk.Checkbutton(r4, text="-trans_raster3d",
                            variable=self.var_trans_raster).pack(side="left")
            ttk.Label(r4, text="线程数:").pack(side="left", padx=(15, 0))
            self.var_threads = tk.StringVar(value="4")
            ttk.Combobox(r4, textvariable=self.var_threads, width=4,
                         values=["1", "2", "4", "8", "16", "28"], state="readonly"
                         ).pack(side="left", padx=5)

            # ── 输出目录 ──
            frm3 = ttk.LabelFrame(root, text="输出目录（默认与输入同目录）")
            frm3.pack(fill="x", padx=10, pady=5)
            self.var_out = tk.StringVar()
            ttk.Entry(frm3, textvariable=self.var_out, width=55).pack(
                side="left", fill="x", expand=True, padx=5, pady=5)
            ttk.Button(frm3, text="浏览", command=self._browse_out).pack(
                side="right", padx=5, pady=5)

            # ── 按钮 ──
            frm4 = ttk.Frame(root); frm4.pack(fill="x", padx=10, pady=5)
            self.btn_run = ttk.Button(frm4, text="  生成 cube  ", command=self._run)
            self.btn_run.pack(side="left", padx=5)
            self.btn_preview = ttk.Button(frm4, text="  预览(单轨道)  ", command=self._preview,
                                          state="disabled")
            self.btn_preview.pack(side="left", padx=5)
            self.btn_preview_multi = ttk.Button(frm4, text="  预览(多轨道)  ", command=self._preview_multi,
                                               state="disabled")
            self.btn_preview_multi.pack(side="left", padx=5)
            self.btn_render = ttk.Button(frm4, text="  渲染当前视角  ", command=self._render_view,
                                         state="disabled")
            self.btn_render.pack(side="left", padx=5)
            self.btn_stop = ttk.Button(frm4, text="  停止  ", command=self._stop,
                                       state="disabled")
            self.btn_stop.pack(side="left", padx=5)

            # ── 隐藏氢原子 ──
            frm_h = ttk.LabelFrame(root, text="隐藏氢原子 (预览后可用)")
            frm_h.pack(fill="x", padx=10, pady=5)

            f_h = ttk.Frame(frm_h); f_h.pack(fill="x", padx=5, pady=4)
            self.var_hide_h = tk.BooleanVar(value=False)
            self.var_h_indices = tk.StringVar(value="")
            self.btn_h_filter = ttk.Button(
                f_h, text="隐藏所有氢原子",
                command=self._toggle_h_filter, state="disabled")
            self.btn_h_filter.pack(side="left", padx=5)
            ttk.Label(f_h, text="保留的氢原子序号(逗号分隔，空=全隐藏):").pack(side="left", padx=(10, 2))
            ttk.Entry(f_h, textvariable=self.var_h_indices, width=20).pack(side="left", padx=2)

            # ── 画虚线设置 ──
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

            # ── 进度 ──
            self.var_prog = tk.StringVar(value="就绪")
            ttk.Label(root, textvariable=self.var_prog).pack(fill="x", padx=10)

            # ── 日志 ──
            self.log = tk.Text(root, height=6, font=("Consolas", 9),
                               bg="#1e1e1e", fg="#d4d4d4", insertbackground="white")
            self.log.pack(fill="both", expand=True, padx=10, pady=5)

            # ── 键盘快捷键：实时调节等值面和透明度 ──
            self.current_iso = 0.05      # 当前等值面值
            self.current_opacity = None   # 当前透明度 (None=样式默认)
            self.iso_step = 0.005
            self.opacity_step = 0.05

            root.bind("<Prior>", self._key_iso_up)       # PageUp
            root.bind("<Next>", self._key_iso_down)       # PageDown
            root.bind("<Home>", self._key_opacity_up)     # Home
            root.bind("<End>", self._key_opacity_down)    # End

        def _add_orbital(self, orb):
            """将轨道添加到现有轨道列表（用于快捷按钮）"""
            current = self.var_orbital.get().strip()
            if not current:
                self.var_orbital.set(orb)
            else:
                orbs = [x.strip() for x in current.split(',') if x.strip()]
                if orb not in orbs:
                    orbs.append(orb)
                    self.var_orbital.set(','.join(orbs))

        def _get_orbitals(self):
            """解析轨道输入框，支持逗号分隔的多个轨道"""
            orb_str = self.var_orbital.get().strip()
            if not orb_str:
                return []
            return [x.strip() for x in orb_str.split(',') if x.strip()]

        def _extract_orbital_name(self, cube_path):
            """从 cube 文件名中提取轨道名称（如从 xxx_MOh.cub 提取 h）"""
            basename = os.path.basename(cube_path)
            name_without_ext = os.path.splitext(basename)[0]
            if '_MO' in name_without_ext:
                return name_without_ext.rsplit('_MO', 1)[1]
            return name_without_ext

        def _get_style_name(self):
            """从下拉框获取样式名（去掉描述部分）"""
            val = self.var_style.get().strip()
            if val:
                return val.split("  ")[0].strip()
            return "sob-art"

        def _browse_exe(self, which):
            if which == "multiwfn":
                p = filedialog.askopenfilename(title="选择 Multiwfn.exe",
                    filetypes=[("Executable", "*.exe")])
                if p:
                    self.var_mw.set(p)
            elif which == "vmd":
                p = filedialog.askopenfilename(title="选择 VMD 可执行文件",
                    filetypes=[("Executable", "*.exe")])
                if p:
                    self.var_vmd.set(p)

        def _save_paths(self):
            vmd = self.var_vmd.get().strip()
            tachyon = os.path.join(os.path.dirname(vmd), "tachyon_WIN32.exe")
            save_config(self.var_mw.get().strip(), vmd, tachyon)

        def _get_paths(self):
            vmd = self.var_vmd.get().strip()
            tachyon = os.path.join(os.path.dirname(vmd), "tachyon_WIN32.exe")
            return {
                "multiwfn": self.var_mw.get().strip(),
                "vmd": vmd,
                "tachyon": tachyon,
            }

        def _browse(self):
            if self.var_mode.get() == "folder":
                p = filedialog.askdirectory(title="选择含 .fchk 的文件夹")
            else:
                p = filedialog.askopenfilename(
                    title="选择 .fchk",
                    filetypes=[("Formatted Checkpoint", "*.fchk")])
            if p:
                self.var_path.set(p)

        def _browse_out(self):
            p = filedialog.askdirectory(title="选择输出目录")
            if p:
                self.var_out.set(p)

        def _append(self, msg):
            self.log.insert("end", msg + "\n")
            self.log.see("end")
            self.root.update_idletasks()

        def _get_params(self):
            orbitals = self._get_orbitals()
            orbital = orbitals[0] if orbitals else ""
            try:
                iso = float(self.var_iso.get().strip())
            except ValueError:
                iso = 0.05
            grid = self.var_grid.get().strip()
            style_name = self._get_style_name()
            try:
                res_str = self.var_res.get().strip()
                w, h = res_str.split("x")
                resolution = (int(w), int(h))
            except (ValueError, AttributeError):
                resolution = (2000, 1500)
            return orbital, iso, grid, style_name, resolution, self.var_shade.get()

        def _fchk_to_png_name(self, fchk_path, out_dir):
            orbital = self.var_orbital.get().strip()
            stem = os.path.splitext(os.path.basename(fchk_path))[0]
            return os.path.join(out_dir, f"{stem}_MO{orbital}.png")

        def _run(self):
            if self.running:
                return
            path = self.var_path.get().strip()
            if not path:
                messagebox.showwarning("提示", "请先选择文件或文件夹")
                return

            exe_paths = self._get_paths()
            if not os.path.exists(exe_paths["multiwfn"]):
                messagebox.showwarning("路径错误", f"Multiwfn 不存在:\n{exe_paths['multiwfn']}")
                return
            if not os.path.exists(exe_paths["vmd"]):
                messagebox.showwarning("路径错误", f"VMD 不存在:\n{exe_paths['vmd']}")
                return

            self._save_paths()

            files = (sorted(glob.glob(os.path.join(path, "*.fchk")))
                     if os.path.isdir(path) else [path])
            if not files:
                messagebox.showwarning("提示", "未找到 .fchk 文件")
                return

            out = self.var_out.get().strip() or (
                path if os.path.isdir(path) else os.path.dirname(path))
            os.makedirs(out, exist_ok=True)

            orbital_str, iso, grid, style_name, resolution, shade_mode = self._get_params()
            orbitals = self._get_orbitals()
            if not orbitals:
                messagebox.showwarning("提示", "请先输入轨道编号")
                return
            orbital = orbitals[0]

            auto = self.var_auto.get()
            do_open = self.var_open.get()
            is_multi = len(orbitals) > 1

            self.running = True
            self.btn_run.config(state="disabled")
            self.btn_stop.config(state="normal")
            self.btn_preview.config(state="disabled")
            self.btn_preview_multi.config(state="disabled")
            self.btn_render.config(state="disabled")

            def worker():
                total = len(files)
                self._append(f"{total} 个文件 -> {out}")
                if is_multi:
                    self._append(f"轨道=[{','.join(orbitals)}]  iso={iso}  grid={grid}  样式={style_name}  res={resolution[0]}x{resolution[1]}")
                else:
                    self._append(f"轨道={orbital}  iso={iso}  grid={grid}  样式={style_name}  res={resolution[0]}x{resolution[1]}")
                if auto:
                    self._append("模式: 自动渲染（无预览）")
                else:
                    self._append("模式: 生成 cube -> 手动预览 -> 渲染")
                self._append("=" * 50)
                ok = 0
                cubes = []
                t_total = time.time()
                for i, fchk in enumerate(files):
                    if not self.running:
                        self._append("已停止"); break
                    name = os.path.basename(fchk)
                    self.var_prog.set(f"[{i+1}/{total}] {name}")
                    self._append(f"\n[{i+1}/{total}] {name}")

                    t0 = time.time()
                    if is_multi:
                        results = gen_multi_cubes(fchk, orbitals,
                                               grid_quality=int(grid), work_dir=out,
                                               multiwfn_exe=exe_paths["multiwfn"])
                        dt = time.time() - t0
                        if results:
                            for cube_path, orb_name in results:
                                self._append(f"  cube OK ({orb_name}) -> {os.path.basename(cube_path)}")
                                cubes.append((cube_path, orb_name))
                            ok += 1
                        else:
                            self._append(f"  cube 生成失败 ({dt:.1f}s)")
                    else:
                        cube = gen_cube(fchk, orbital=orbital,
                                       grid_quality=int(grid), work_dir=out,
                                       multiwfn_exe=exe_paths["multiwfn"])
                        dt = time.time() - t0
                        if not cube:
                            self._append(f"  cube 失败 ({dt:.1f}s)")
                            continue
                        self._append(f"  cube OK ({dt:.1f}s) -> {os.path.basename(cube)}")
                        cubes.append(cube)
                        ok += 1

                    if auto:
                        t0 = time.time()
                        try:
                            png = self._fchk_to_png_name(fchk, out)
                            render_cube_auto(cube if not is_multi else cubes[-1][0], output_png=png, isovalue=iso,
                                             style_name=style_name, resolution=resolution,
                                             vmd_exe=exe_paths["vmd"],
                                             tachyon_exe=exe_paths["tachyon"],
                                             shade_mode=shade_mode)
                            dt = time.time() - t0
                            self._append(f"  PNG: {os.path.basename(png)} ({dt:.1f}s)")
                        except Exception as e:
                            self._append(f"  渲染错误: {e}")

                elapsed = time.time() - t_total
                self._append(f"\ncube 生成完毕: {ok}/{total}，耗时 {elapsed:.1f}s")

                if not auto and cubes:
                    self._append("\n在 VMD 中调整好视角后，点击 [预览(单轨道)]、[预览(多轨道)] 或 [渲染当前视角]")
                    self.btn_preview.config(state="normal")
                    if is_multi:
                        self.btn_preview_multi.config(state="normal")

                if auto:
                    self._append(f"\n全部完成 {ok}/{total}")
                    self.var_prog.set(f"完成: {ok}/{total}")
                    if do_open and ok > 0:
                        os.startfile(out)

                self.running = False
                self.btn_run.config(state="normal")
                self.btn_stop.config(state="disabled")

            threading.Thread(target=worker, daemon=True).start()

        def _preview(self):
            path = self.var_path.get().strip()
            out = self.var_out.get().strip() or (
                path if os.path.isdir(path) else os.path.dirname(path))

            cubes = sorted(glob.glob(os.path.join(out, "*.cub")))
            if not cubes:
                messagebox.showwarning("提示", "输出目录中没有 .cub 文件")
                return

            if os.path.isfile(path):
                stem = os.path.splitext(os.path.basename(path))[0]
                target = [c for c in cubes if stem in c]
                if target:
                    cubes = target

            if len(cubes) == 1:
                cube_path = cubes[0]
            else:
                import tkinter as tk
                from tkinter import simpledialog, messagebox

                class CubeSelector(tk.Toplevel):
                    def __init__(self, parent, cubes):
                        super().__init__(parent)
                        self.title("选择要预览的 cube 文件")
                        self.geometry("500x400")
                        self.result = None

                        frame = tk.Frame(self, padx=10, pady=10)
                        frame.pack(fill="both", expand=True)

                        tk.Label(frame, text="请选择要预览的 cube 文件:").pack(anchor="w", pady=5)

                        self.listbox = tk.Listbox(frame, width=60, height=15)
                        self.listbox.pack(fill="both", expand=True)
                        for cube in cubes:
                            self.listbox.insert(tk.END, os.path.basename(cube))
                        self.listbox.bind("<Double-1>", self.on_select)
                        self.listbox.selection_set(0)

                        btn_frame = tk.Frame(frame)
                        btn_frame.pack(fill="x", pady=10)
                        tk.Button(btn_frame, text="确定", command=self.on_select).pack(side="right", padx=5)
                        tk.Button(btn_frame, text="取消", command=self.destroy).pack(side="right")

                        self.transient(parent)
                        self.grab_set()

                    def on_select(self, event=None):
                        selection = self.listbox.curselection()
                        if selection:
                            self.result = cubes[selection[0]]
                            self.destroy()

                selector = CubeSelector(self.root, cubes)
                self.root.wait_window(selector)
                if selector.result:
                    cube_path = selector.result
                else:
                    return

            self.vmd_cube_path = cube_path
            orbital, iso, grid, style_name, resolution, shade_mode = self._get_params()
            exe_paths = self._get_paths()

            # 解析隐藏氢原子配置
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

            # 同步键盘调节的当前值
            self.current_iso = iso
            self.current_opacity = None  # 重置，下次按 Home/End 时读取样式默认值

            self._append(f"\n启动 VMD 预览: {os.path.basename(cube_path)}")
            self._append(f"样式: {style_name}")
            self._append("请在 VMD 中调整视角，然后点击 [渲染当前视角]")

            try:
                port, render_dir = preview_cube(cube_path, isovalue=iso,
                                                style_name=style_name,
                                                vmd_exe=exe_paths["vmd"],
                                                shade_mode=shade_mode,
                                                keep_h_indices=keep_h_indices)
                if port:
                    self.vmd_port = port
                    self.vmd_render_dir = render_dir
                    self.btn_render.config(state="normal")
                    self.btn_draw_bond.config(state="normal")
                    self.btn_undo_bond.config(state="normal")
                    self.btn_clear_bond.config(state="normal")
                    self.btn_h_filter.config(state="normal")
                    self._current_iso = iso
                    self._current_style_name = style_name
                    self._append(f"VMD 已启动 (端口 {port})，等待操作...")
                else:
                    self._append("VMD 启动失败")
            except Exception as e:
                self._append(f"VMD 启动错误: {e}")

        def _preview_multi(self):
            """预览多个轨道的等值面"""
            path = self.var_path.get().strip()
            out = self.var_out.get().strip() or (
                path if os.path.isdir(path) else os.path.dirname(path))

            all_cubes = sorted(glob.glob(os.path.join(out, "*_MO*.cub")))
            if not all_cubes:
                messagebox.showwarning("提示", "输出目录中没有找到轨道 cube 文件\n请先点击 [生成 cube]")
                return

            if len(all_cubes) == 1:
                cube_path = all_cubes[0]
                cubes = [(cube_path, self._extract_orbital_name(cube_path))]
            else:
                import tkinter as tk
                from tkinter import messagebox

                class MultiCubeSelector(tk.Toplevel):
                    def __init__(self, parent, cubes):
                        super().__init__(parent)
                        self.title("选择要预览的轨道")
                        self.geometry("500x450")
                        self.result = None
                        self.cubes = cubes  

                        frame = tk.Frame(self, padx=10, pady=10)
                        frame.pack(fill="both", expand=True)

                        tk.Label(frame, text="请选择要预览的轨道（可多选，按住 Ctrl 或 Shift）:").pack(anchor="w", pady=5)

                        self.listbox = tk.Listbox(frame, width=60, height=15, selectmode="extended")
                        self.listbox.pack(fill="both", expand=True)
                        for cube in cubes:
                            self.listbox.insert(tk.END, os.path.basename(cube))
                        self.listbox.selection_set(0, len(cubes)-1)

                        btn_frame = tk.Frame(frame)
                        btn_frame.pack(fill="x", pady=10)
                        tk.Button(btn_frame, text="全选", command=self.select_all).pack(side="left", padx=5)
                        tk.Button(btn_frame, text="反选", command=self.select_invert).pack(side="left", padx=5)
                        tk.Button(btn_frame, text="确定", command=self.on_select).pack(side="right", padx=5)
                        tk.Button(btn_frame, text="取消", command=self.destroy).pack(side="right")

                        self.transient(parent)
                        self.grab_set()

                    def select_all(self):
                        self.listbox.select_set(0, tk.END)

                    def select_invert(self):
                        for i in range(self.listbox.size()):
                            if self.listbox.selection_includes(i):
                                self.listbox.selection_clear(i)
                            else:
                                self.listbox.selection_set(i)

                    def on_select(self):
                        selection = self.listbox.curselection()
                        if selection:
                            self.result = [self.cubes[i] for i in selection]
                            self.destroy()

                selector = MultiCubeSelector(self.root, all_cubes)
                self.root.wait_window(selector)
                if not selector.result:
                    return

                cubes = [(cube, self._extract_orbital_name(cube)) for cube in selector.result]

            orbitals = [orb for _, orb in cubes]

            try:
                iso = float(self.var_iso.get().strip())
            except ValueError:
                iso = 0.05

            style_name = self._get_style_name()
            shade_mode = self.var_shade.get()
            # Bug fix: 正确解析分辨率字符串
            try:
                res_str = self.var_res.get().strip()
                res_w, res_h = res_str.split("x")
                resolution = (int(res_w), int(res_h))
            except (ValueError, AttributeError):
                resolution = (2000, 1500)
            exe_paths = self._get_paths()

            # 解析隐藏氢原子配置
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

            self.current_iso = iso
            self.current_opacity = None

            orb_names = ", ".join([orb for _, orb in cubes])
            self._append(f"\n启动 VMD 多轨道预览: {orb_names}")
            self._append(f"样式: {style_name}, 等值面: {iso}")
            self._append("请在 VMD 中调整视角，然后点击 [渲染当前视角]")

            try:
                port, render_dir, copied_cubes = preview_multi_cubes(
                    cubes, iso, style_name=style_name,
                    vmd_exe=exe_paths["vmd"], shade_mode=shade_mode,
                    keep_h_indices=keep_h_indices)
                if port:
                    self.vmd_port = port
                    self.vmd_render_dir = render_dir
                    self.vmd_multi_cubes = copied_cubes
                    self.btn_render.config(state="normal")
                    self.btn_draw_bond.config(state="normal")
                    self.btn_undo_bond.config(state="normal")
                    self.btn_clear_bond.config(state="normal")
                    self.btn_h_filter.config(state="normal")
                    self._current_iso = iso
                    self._current_style_name = style_name
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

            _, _, _, style_name, resolution, shade_mode = self._get_params()
            exe_paths = self._get_paths()

            # 生成输出文件名：与 fchk 文件名一致
            output_png = None
            if self.vmd_cube_path:
                cube_stem = os.path.splitext(os.path.basename(self.vmd_cube_path))[0]
                fchk_name = cube_stem.rsplit("_MO", 1)[0]
                orbital = self.var_orbital.get().strip()
                output_png = os.path.join(out, f"{fchk_name}_MO{orbital}.png") if out else None
            elif self.vmd_multi_cubes and self.vmd_multi_cubes[0][0]:
                # 多轨道模式：使用第一个 cube 文件的 fchk 名称
                cube_stem = os.path.splitext(os.path.basename(self.vmd_multi_cubes[0][0]))[0]
                fchk_name = cube_stem.rsplit("_MO", 1)[0]
                orbitals = self._get_orbitals()
                orbital_suffix = "_".join(orbitals) if orbitals else "multi"
                output_png = os.path.join(out, f"{fchk_name}_MO{orbital_suffix}.png") if out else None

            # 获取 Tachyon 参数
            trans_raster = self.var_trans_raster.get()
            threads = int(self.var_threads.get())

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
                        trans_raster=trans_raster,
                        threads=threads,
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

        def _stop(self):
            self.running = False
            self.btn_stop.config(state="disabled")

        def _toggle_h_filter(self):
            """切换氢原子显示/隐藏（预览模式下实时发送 TCL 命令）
            原理：用 mol modselect 0 molID "..." 只控制原子球棍(representation 0)的显示选择，
            不影响等值面(representation 1/2)，避免 pdb 中转丢失 cube 数据。
            多轨道模式下需要遍历所有分子 ID。
            """
            if not hasattr(self, 'vmd_port') or not self.vmd_port:
                self._append("请先点击预览按钮启动 VMD")
                return

            self.var_hide_h.set(not self.var_hide_h.get())
            if self.var_hide_h.get():
                self.btn_h_filter.config(text="显示所有氢原子")
                # 构建选择字符串：rep 0 只显示非氢（或保留指定氢）
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
                # 遍历所有分子 ID，对每个的 rep 0 执行 modselect
                cmd = (
                    f'foreach mid [molinfo list] {{'
                    f'  mol modselect 0 $mid "{sel_str}"'
                    f'}}'
                )
                self._send_vmd_cmd(cmd)
                self._append("[隐藏氢] 已隐藏所有分子的氢原子")
            else:
                self.btn_h_filter.config(text="隐藏所有氢原子")
                # 恢复：所有分子的 rep 0 显示全部原子
                cmd = 'foreach mid [molinfo list] { mol modselect 0 $mid all }'
                self._send_vmd_cmd(cmd)
                self._append("[隐藏氢] 已恢复所有分子的氢原子")

        def _send_vmd_cmd(self, cmd):
            """通过 socket 向 VMD 发送一条 TCL 命令并返回响应。"""
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

        def _key_iso_up(self, event=None):
            """PageUp: 增大等值面"""
            self.current_iso = round(min(self.current_iso + self.iso_step, 0.5), 4)
            self._apply_iso_change()

        def _key_iso_down(self, event=None):
            """PageDown: 减小等值面"""
            self.current_iso = round(max(self.current_iso - self.iso_step, 0.005), 4)
            self._apply_iso_change()

        def _key_opacity_up(self, event=None):
            """Home: 增大透明度（更不透明）"""
            if self.current_opacity is None:
                # 第一次按 Home/End，读取当前样式的 opacity 作为基准
                style = STYLES.get(self._get_style_name(), STYLES["sob-art"])
                self.current_opacity = style["surface_mat"][5]
            self.current_opacity = round(min(self.current_opacity + self.opacity_step, 1.0), 2)
            self._apply_opacity_change()

        def _key_opacity_down(self, event=None):
            """End: 减小透明度（更透明）"""
            if self.current_opacity is None:
                style = STYLES.get(self._get_style_name(), STYLES["sob-art"])
                self.current_opacity = style["surface_mat"][5]
            self.current_opacity = round(max(self.current_opacity - self.opacity_step, 0.05), 2)
            self._apply_opacity_change()

        def _apply_iso_change(self):
            """发送 TCL 命令更新等值面，同步 GUI。"""
            iso = self.current_iso
            self.var_iso.set(f"{iso:.4g}")
            # 更新正负等值面 (mol modstyle 1/2 top Isosurface ±value ...)
            cmd = f"mol modstyle 1 top Isosurface {iso} 0 0 0 1 1"
            resp1 = self._send_vmd_cmd(cmd)
            cmd = f"mol modstyle 2 top Isosurface -{iso} 0 0 0 1 1"
            resp2 = self._send_vmd_cmd(cmd)
            status = "OK" if resp1 and "ERROR" not in (resp1 + (resp2 or "")) else "VMD 未连接"
            self._append(f"[等值面] iso = {iso:.4g}  ({status})")

        def _apply_opacity_change(self):
            """发送 TCL 命令更新透明度，同步 GUI。"""
            op = self.current_opacity
            # 同时更新正负等值面的材质透明度
            for mat_name in ["_stl_a", "_stl_b"]:
                cmd = f"material change opacity {mat_name} {op}"
                self._send_vmd_cmd(cmd)
            self._append(f"[透明度] opacity = {op:.2f}")

        def _draw_bond(self):
            """画虚线：在两个原子之间绘制连接"""
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
            """撤销上一条画的虚线"""
            resp = self._send_vmd_cmd("draw_bond_undo")
            if resp and "ERROR" not in resp:
                self._append("[虚线] 撤销")
            else:
                self._append("[虚线] 撤销失败")

        def _clear_bond(self):
            """清除所有画的虚线"""
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
        p = argparse.ArgumentParser(description="Multiwfn + VMD/Tachyon 轨道等值面可视化 v4")
        p.add_argument("input", help="fchk 文件或文件夹")
        p.add_argument("--mo", default="h", help="轨道 (h/l/h-1/数字)")
        p.add_argument("--iso", type=float, default=0.05, help="等值面阈值")
        p.add_argument("--grid", default="2", help="网格质量 (1/2/3)")
        p.add_argument("--style", default="sob_Gold",
                       choices=list(STYLES.keys()), help="渲染样式")
        p.add_argument("--res", default="2000,1500", help="分辨率 宽,高")
        p.add_argument("--no-render", action="store_true", help="只生成 cube，不渲染")
        p.add_argument("--out", default=None)
        a = p.parse_args()

        files = sorted(glob.glob(os.path.join(a.input, "*.fchk"))) if os.path.isdir(a.input) else [a.input]
        out = a.out or (os.path.dirname(a.input) if os.path.isfile(a.input) else a.input)
        os.makedirs(out, exist_ok=True)

        w, h = [int(x) for x in a.res.split(",")]

        for i, f in enumerate(files):
            print(f"[{i+1}/{len(files)}] {os.path.basename(f)}")
            cube = gen_cube(f, orbital=a.mo, grid_quality=int(a.grid), work_dir=out)
            if cube:
                print(f"  cube: {os.path.basename(cube)}")
                if not a.no_render:
                    png = render_cube_auto(cube, isovalue=a.iso,
                                           style_name=a.style, resolution=(w, h))
                    if png:
                        print(f"  png:  {os.path.basename(png)}")
            else:
                print(f"  失败")
    else:
        launch_gui()


if __name__ == "__main__":
    main()


