#!/usr/bin/env python3
"""
NBO E(2) Analysis + Orbital Visualization GUI  v3.0
=============================================
PyQt5 + PyVista rewrite.

Features:
  1. Select Gaussian NBO .log + fchk files
  2. Input two atom numbers
  3. Analyze NBO E(2) interactions
  4. PyVista 3D molecule preview (rotate/zoom/select atoms)
  5. Multiwfn cube gen -> VMD preview -> render PNG
  6. Real-time isovalue/opacity sliders

Usage:
  python nbo_gui_v3.py

Dependencies:
  - Python 3.8+
  - PyQt5
  - PyVista + pyvistaqt
  - Multiwfn
  - VMD (optional)
"""

import sys
import re
import os
import threading
import subprocess
import tempfile
import shutil
import json
import math
import socket
import time
import numpy as np

from pathlib import Path
from datetime import datetime
from collections import Counter

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QFileDialog, QMessageBox, QSplitter, QTabWidget,
    QScrollArea, QGroupBox, QRadioButton, QButtonGroup,
    QTextEdit, QApplication, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QSlider, QStatusBar, QMenuBar,
    QAction, QDialog, QFormLayout, QDialogButtonBox, QFrame,
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QThread, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon

import pyvista as pv
from pyvistaqt import QtInteractor

CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "nbo_gui_config.json"
)

DEFAULT_MULTIWFN = r"E:\Multiwfn_2026.4.10_bin_Win64\Multiwfn.exe"
DEFAULT_VMD = r"C:\Program Files (x86)\University of Illinois\VMD\vmd.exe"
DEFAULT_TACHYON = r"C:\Program Files (x86)\University of Illinois\VMD\tachyon_WIN32.exe"


def load_config():
    """从 JSON 文件读取路径配置"""
    paths = {
        "multiwfn": DEFAULT_MULTIWFN,
        "vmd": DEFAULT_VMD,
        "tachyon": DEFAULT_TACHYON,
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                user_paths = json.load(f)
            for k in paths:
                if k in user_paths and user_paths[k]:
                    paths[k] = user_paths[k]
        except Exception:
            pass
    return paths


def save_config(multiwfn, vmd, tachyon):
    """保存路径配置到 JSON 文件"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"multiwfn": multiwfn, "vmd": vmd, "tachyon": tachyon},
                  f, indent=2, ensure_ascii=False)


# =====================================================================
#  分子结构解析（从 fchk/log 文件提取原子坐标）
# =====================================================================

def parse_fchk_atoms(fchk_file):
    """
    从 fchk 文件解析原子坐标
    返回: list of dict, 每个包含 {'elem': 元素符号, 'x': x坐标, 'y': y坐标, 'z': z坐标, 'idx': 原子编号}
    """
    atoms = []
    with open(fchk_file, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    
    # 提取原子数
    natom_match = re.search(r"Number of atoms\s+I\s+N=\s*(\d+)", content)
    if not natom_match:
        return []
    natom = int(natom_match.group(1))
    
    # 提取元素符号
    elem_section = re.search(r"Atomic Numbers\s+I\s+N=\s*(\d+)(.*?)(?=\s*[A-Za-z])", content, re.DOTALL)
    if elem_section:
        elem_count = int(elem_section.group(1))
        elem_data = elem_section.group(2)
        elem_nums = [int(x) for x in elem_data.split() if x.strip()]
        elem_nums = elem_nums[:natom]
    else:
        return []
    
    # 提取坐标
    coord_section = re.search(r"Current cartesian coordinates\s+R\s+N=\s*(\d+)(.*?)(?=\s*[A-Za-z])", content, re.DOTALL)
    if coord_section:
        coord_count = int(coord_section.group(1))
        coord_data = coord_section.group(2)
        coords = [float(x) for x in coord_data.split() if x.strip()]
        coords = coords[:natom * 3]
    else:
        return []
    
    # 元素编号到符号的映射
    elem_map = {1: 'H', 2: 'He', 3: 'Li', 4: 'Be', 5: 'B', 6: 'C', 7: 'N', 8: 'O', 
                9: 'F', 10: 'Ne', 11: 'Na', 12: 'Mg', 13: 'Al', 14: 'Si', 15: 'P', 
                16: 'S', 17: 'Cl', 18: 'Ar', 19: 'K', 20: 'Ca', 26: 'Fe', 27: 'Co'}
    
    for i in range(natom):
        atoms.append({
            'idx': i + 1,
            'elem': elem_map.get(elem_nums[i], f'X{elem_nums[i]}'),
            'x': coords[i * 3],
            'y': coords[i * 3 + 1],
            'z': coords[i * 3 + 2]
        })
    
    return atoms


def _atomic_num_to_symbol(num):
    """Convert atomic number to element symbol"""
    _TABLE = {
        1: "H", 2: "He", 3: "Li", 4: "Be", 5: "B", 6: "C", 7: "N", 8: "O",
        9: "F", 10: "Ne", 11: "Na", 12: "Mg", 13: "Al", 14: "Si", 15: "P",
        16: "S", 17: "Cl", 18: "Ar", 19: "K", 20: "Ca", 21: "Sc", 22: "Ti",
        23: "V", 24: "Cr", 25: "Mn", 26: "Fe", 27: "Co", 28: "Ni", 29: "Cu",
        30: "Zn", 31: "Ga", 32: "Ge", 33: "As", 34: "Se", 35: "Br", 36: "Kr",
        37: "Rb", 38: "Sr", 39: "Y", 40: "Zr", 41: "Nb", 42: "Mo", 43: "Tc",
        44: "Ru", 45: "Rh", 46: "Pd", 47: "Ag", 48: "Cd", 49: "In", 50: "Sn",
        51: "Sb", 52: "Te", 53: "I", 54: "Xe", 55: "Cs", 56: "Ba", 57: "La",
        72: "Hf", 73: "Ta", 74: "W", 75: "Re", 76: "Os", 77: "Ir", 78: "Pt",
        79: "Au", 80: "Hg", 81: "Tl", 82: "Pb", 83: "Bi",
    }
    return _TABLE.get(num, f"X{num}")

def parse_log_atoms(log_file):
    """
    从 log 文件解析原子坐标（支持多种格式）
    返回: list of dict, 每个包含 {'elem': 元素符号, 'x': x坐标, 'y': y坐标, 'z': z坐标, 'idx': 原子编号}
    """
    atoms = []
    
    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception:
        return atoms
    
    lines = content.strip().splitlines()
    
    # 方法1: 尝试解析为 XYZ 格式
    atoms = _parse_xyz_content(content)
    if atoms:
        return atoms
    
    # 方法2: 尝试解析为 gjf/com 格式
    atoms = _parse_gjf_content(content)
    if atoms:
        return atoms
    
    # 方法3: 解析 Gaussian log 格式（Standard orientation 或 Input orientation）
    atoms = _parse_gaussian_log_content(lines)
    if atoms:
        return atoms
    
    # 方法4: 尝试从 "ATOM" 行解析（Gaussian 输出的另一种格式）
    atoms = _parse_atom_lines(lines)
    if atoms:
        return atoms
    
    return atoms

def _parse_xyz_content(content):
    """Parse XYZ format"""
    lines = content.strip().splitlines()
    if len(lines) < 3:
        return []
    try:
        natoms = int(lines[0].strip())
    except ValueError:
        return []
    atoms = []
    for i in range(2, min(2 + natoms, len(lines))):
        parts = lines[i].split()
        if len(parts) < 4:
            continue
        try:
            symbol = parts[0]
            if symbol[0].isalpha():
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                atoms.append({
                    'idx': len(atoms) + 1,
                    'elem': symbol.capitalize(),
                    'x': x,
                    'y': y,
                    'z': z
                })
        except (ValueError, IndexError):
            continue
    return atoms if len(atoms) > 0 else []

def _parse_gjf_content(content):
    """Parse Gaussian gjf/com format"""
    lines = content.strip().splitlines()
    atoms = []
    # gjf structure: route → blank line → title → blank line → charge multiplicity → coordinates → blank line
    blank_count = 0
    past_header = False
    for line in lines:
        stripped = line.strip()
        if not past_header:
            if not stripped:
                blank_count += 1
            if blank_count >= 2:
                past_header = True
            continue
        # After header, first line is charge/multiplicity
        if not atoms:
            parts = stripped.split()
            if len(parts) >= 2:
                try:
                    int(parts[0])
                    # 这行是电荷/多重度，跳过
                    continue
                except ValueError:
                    pass
            # If not charge/multiplicity line, treat as coordinate line
        # 解析坐标行
        if not stripped:
            if atoms:
                break  # End of coordinate section
            continue
        parts = stripped.split()
        if len(parts) >= 4:
            try:
                sym = parts[0]
                if sym.isdigit():
                    sym = _atomic_num_to_symbol(int(sym))
                elif sym[0].isalpha():
                    sym = sym.capitalize()
                else:
                    continue
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                atoms.append({
                    'idx': len(atoms) + 1,
                    'elem': sym,
                    'x': x,
                    'y': y,
                    'z': z
                })
            except (ValueError, IndexError):
                if atoms:
                    break
        else:
            if atoms:
                break
    return atoms if len(atoms) > 0 else []

def _parse_gaussian_log_content(lines):
    """Parse Gaussian log file format (Standard/Input orientation)"""
    atoms = []
    
    # 查找坐标部分
    in_coords = False
    coord_lines = []
    found_orientation = False
    
    for line in lines:
        if "Standard orientation:" in line or "Input orientation:" in line:
            found_orientation = True
            in_coords = False
            coord_lines = []
            continue
        
        if "Center     Atomic      Atomic             Coordinates (Angstroms)" in line:
            in_coords = True
            continue
        
        if in_coords:
            if "---------------------------------------------------------------------" in line:
                break
            if line.strip() and not line.strip().startswith('-'):
                coord_lines.append(line)
    
    if not found_orientation:
        return []
    
    # 解析坐标行
    for line in coord_lines:
        parts = line.split()
        if len(parts) >= 6:
            try:
                idx = int(parts[0])
                elem = parts[2]
                x = float(parts[3])
                y = float(parts[4])
                z = float(parts[5])
                atoms.append({
                    'idx': idx,
                    'elem': elem.capitalize(),
                    'x': x,
                    'y': y,
                    'z': z
                })
            except ValueError:
                continue
    
    return atoms if len(atoms) > 0 else []

def _parse_atom_lines(lines):
    """Parse ATOM lines (another Gaussian output format)"""
    atoms = []
    
    for line in lines:
        # 匹配 "ATOM" 开头的行
        if line.strip().startswith('ATOM'):
            parts = line.split()
            if len(parts) >= 6:
                try:
                    # ATOM 格式: ATOM  idx  elem  x  y  z
                    idx = int(parts[1])
                    elem = parts[2]
                    x = float(parts[3])
                    y = float(parts[4])
                    z = float(parts[5])
                    atoms.append({
                        'idx': idx,
                        'elem': elem.capitalize(),
                        'x': x,
                        'y': y,
                        'z': z
                    })
                except ValueError:
                    continue
    
    return atoms if len(atoms) > 0 else []


# Covalent Radii (Å) for bond detection
_COVALENT_RADII = {
    "H": 0.31, "He": 0.28, "Li": 1.28, "Be": 0.96, "B": 0.84,
    "C": 0.76, "N": 0.71, "O": 0.66, "F": 0.57, "Ne": 0.58,
    "Na": 1.66, "Mg": 1.41, "Al": 1.21, "Si": 1.11, "P": 1.07,
    "S": 1.05, "Cl": 1.02, "Ar": 1.06, "K": 2.03, "Ca": 1.76,
    "Sc": 1.70, "Ti": 1.60, "V": 1.53, "Cr": 1.39, "Mn": 1.39,
    "Fe": 1.32, "Co": 1.26, "Ni": 1.24, "Cu": 1.32, "Zn": 1.22,
    "Ga": 1.22, "Ge": 1.20, "As": 1.19, "Se": 1.20, "Br": 1.20,
    "Kr": 1.16, "Rb": 2.20, "Sr": 1.95, "Y": 1.90, "Zr": 1.75,
    "Nb": 1.64, "Mo": 1.54, "Tc": 1.47, "Ru": 1.46, "Rh": 1.42,
    "Pd": 1.39, "Ag": 1.45, "Cd": 1.44, "In": 1.42, "Sn": 1.39,
    "Sb": 1.39, "Te": 1.38, "I": 1.39, "Xe": 1.40, "Cs": 2.44,
    "Ba": 2.15, "La": 2.07, "Ce": 2.04, "Pr": 2.03, "Nd": 2.01,
    "Pm": 1.99, "Sm": 1.98, "Eu": 1.98, "Gd": 1.96, "Tb": 1.94,
    "Dy": 1.92, "Ho": 1.92, "Er": 1.89, "Tm": 1.90, "Yb": 1.87,
    "Lu": 1.87, "Hf": 1.75, "Ta": 1.70, "W": 1.62, "Re": 1.51,
    "Os": 1.44, "Ir": 1.41, "Pt": 1.36, "Au": 1.36, "Hg": 1.32,
    "Tl": 1.45, "Pb": 1.46, "Bi": 1.48, "Po": 1.40, "At": 1.50,
    "Rn": 1.50, "Fr": 2.60, "Ra": 2.21, "Ac": 2.15, "Th": 2.06,
    "Pa": 2.00, "U": 1.96, "Np": 1.90, "Pu": 1.87, "Am": 1.80,
    "Cm": 1.69,
}

def calculate_bonds(atoms, cutoff_multiplier=1.2):
    """
    根据原子坐标计算化学键（使用共价半径判断）
    cutoff_multiplier: 键长阈值倍数（共价半径之和 × 此倍数）
    返回: list of tuple (atom_idx1, atom_idx2)
    """
    bonds = []
    n = len(atoms)
    for i in range(n):
        for j in range(i + 1, n):
            atom1 = atoms[i]
            atom2 = atoms[j]
            dx = atom1['x'] - atom2['x']
            dy = atom1['y'] - atom2['y']
            dz = atom1['z'] - atom2['z']
            dist = math.sqrt(dx * dx + dy * dy + dz * dz)
            
            # 使用共价半径判断键
            ri = _COVALENT_RADII.get(atom1['elem'], 1.0)
            rj = _COVALENT_RADII.get(atom2['elem'], 1.0)
            # 键长阈值：共价半径之和 × 1.2
            if dist < (ri + rj) * cutoff_multiplier:
                bonds.append((atom1['idx'], atom2['idx']))
    return bonds


# =====================================================================
#  核心解析逻辑
# =====================================================================

def parse_nbo_summary(log_file):
    """
    解析 log 文件中的 NBO Summary 部分（Natural Bond Orbitals (Summary)）
    返回 dict: nbo_id -> {type, atoms, atom_elems, occupancy, energy}
    """
    nbo_dict = {}
    in_nbo_section = False
    current_unit = ""
    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if "Natural Bond Orbitals (Summary)" in line:
                in_nbo_section = True
                continue
            if not in_nbo_section:
                continue
            m_unit = re.match(r"Molecular unit\s+(\d+)\s+\((.*?)\)", line)
            if m_unit:
                current_unit = m_unit.group(2).strip()
                continue
            m_nbo = re.match(
                r"\s*(\d+)\.\s+(BD|CR|LP|RY|LV)(\*?)\s*\(\s*(\d+)\)\s*([A-Z][a-z]?)\s+(\d+)"
                r"(?:\s*-\s*([A-Z][a-z]?)\s+(\d+))?",
                line
            )
            if m_nbo:
                nbo_id = int(m_nbo.group(1))
                nbo_type = m_nbo.group(2) + (m_nbo.group(3) or "")
                nbo_sub = int(m_nbo.group(4))
                atom1_elem = m_nbo.group(5)
                atom1_num = int(m_nbo.group(6))
                atom2_elem = m_nbo.group(7) if m_nbo.group(7) else None
                atom2_num = int(m_nbo.group(8)) if m_nbo.group(8) else None
                rest = line[m_nbo.end():]
                occ_match = re.search(r"([\d\.]+)\s+([\-\d\.]+)", rest)
                occupancy = float(occ_match.group(1)) if occ_match else None
                energy = float(occ_match.group(2)) if occ_match else None
                atoms = [atom1_num]
                atom_elems = [atom1_elem]
                if atom2_num:
                    atoms.append(atom2_num)
                    atom_elems.append(atom2_elem)
                nbo_dict[nbo_id] = {
                    "type": nbo_type,
                    "sub": nbo_sub,
                    "atoms": atoms,
                    "atom_elems": atom_elems,
                    "occupancy": occupancy,
                    "energy": energy,
                    "unit": current_unit,
                }
                continue
            if any(kw in line for kw in ["Natural Population", "NBO Search", "Second Order"]):
                in_nbo_section = False
    return nbo_dict


def parse_e2_section(log_file):
    """
    解析 Second Order Perturbation Theory Analysis 部分
    返回 list of dict
    """
    e2_list = []
    in_e2_section = False
    current_unit = 1
    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if "Second Order Perturbation Theory Analysis" in line:
                in_e2_section = True
                continue
            if not in_e2_section:
                continue
            m_unit = re.match(r"within unit\s+(\d+)", line)
            if m_unit:
                current_unit = int(m_unit.group(1))
                continue
            stripped = line.strip()
            if stripped and stripped[0].isupper() and len(stripped) > 15:
                if any(kw in stripped for kw in ["Natural Bond", "Natural Population",
                                               "NBO Search", "Job cpu time", "Total cpu time"]):
                    in_e2_section = False
                    continue
            if "Donor NBO" in line or "Threshold" in line or ("E(2)" in line and "kcal" in line):
                continue
            slash_idx = line.find("/")
            if slash_idx < 0:
                continue
            donor_part = line[:slash_idx].rstrip()
            acceptor_rest = line[slash_idx + 1:].lstrip()
            m_donor = re.match(
                r"\s*(\d+)\.\s+(BD|CR|LP|RY)(\*?)\s*\(\s*(\d+)\)\s*([A-Z][a-z]?)\s+(\d+)"
                r"(?:\s*-\s*([A-Z][a-z]?)\s+(\d+))?",
                donor_part
            )
            if not m_donor:
                continue
            donor_id = int(m_donor.group(1))
            donor_type_raw = m_donor.group(2) + (m_donor.group(3) if m_donor.group(3) else "")
            donor_sub = int(m_donor.group(4))
            donor_atom1_elem = m_donor.group(5)
            donor_atom1 = int(m_donor.group(6))
            donor_atom2_elem = m_donor.group(7) if m_donor.group(7) else None
            donor_atom2 = int(m_donor.group(8)) if m_donor.group(8) else None

            m_acceptor = re.match(
                r"(\d+)\.\s+(BD|CR|LP|RY)(\*?)\s*\(\s*(\d+)\)\s*([A-Z][a-z]?)\s+(\d+)"
                r"(?:\s*-\s*([A-Z][a-z]?)\s+(\d+))?",
                acceptor_rest
            )
            if not m_acceptor:
                continue
            acceptor_id = int(m_acceptor.group(1))
            acceptor_type_raw = m_acceptor.group(2) + (m_acceptor.group(3) if m_acceptor.group(3) else "")
            acceptor_sub = int(m_acceptor.group(4))
            acceptor_atom1_elem = m_acceptor.group(5)
            acceptor_atom1 = int(m_acceptor.group(6))
            acceptor_atom2_elem = m_acceptor.group(7) if m_acceptor.group(7) else None
            acceptor_atom2 = int(m_acceptor.group(8)) if m_acceptor.group(8) else None

            rest = acceptor_rest[m_acceptor.end():]
            vals = re.findall(r"([\d\.]+)", rest)
            if len(vals) >= 3:
                e2 = float(vals[0])
                delta_e = float(vals[1])
                fij = float(vals[2])
            else:
                e2 = delta_e = fij = None
            e2_list.append({
                "donor_id": donor_id,
                "donor_type_raw": donor_type_raw,
                "donor_sub": donor_sub,
                "donor_atom1": donor_atom1,
                "donor_atom1_elem": donor_atom1_elem,
                "donor_atom2": donor_atom2,
                "donor_atom2_elem": donor_atom2_elem,
                "acceptor_id": acceptor_id,
                "acceptor_type_raw": acceptor_type_raw,
                "acceptor_sub": acceptor_sub,
                "acceptor_atom1": acceptor_atom1,
                "acceptor_atom1_elem": acceptor_atom1_elem,
                "acceptor_atom2": acceptor_atom2,
                "acceptor_atom2_elem": acceptor_atom2_elem,
                "e2": e2,
                "delta_e": delta_e,
                "fij": fij,
                "unit": current_unit,
                "raw_line": line.rstrip(),
            })
    return e2_list


_FCHK_MO_CACHE = {}

def _load_fchk_mo_energies(fchk_file):
    """读取 fchk 的 MO 能量列表，结果缓存到 _FCHK_MO_CACHE"""
    if fchk_file in _FCHK_MO_CACHE:
        return _FCHK_MO_CACHE[fchk_file]
    alpha_energies = []
    beta_energies = []
    with open(fchk_file, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    sections = re.findall(r"(Alpha|Beta) Orbital Energies\s+R\s+N=\s*(\d+)(.*?)(?=(?:Alpha|Beta) Orbital|\Z)",
                          content, re.DOTALL)
    for sec_type, n_orb, data_block in sections:
        n_orb = int(n_orb)
        raw_vals = []
        for token in data_block.split():
            try:
                val = float(token)
                raw_vals.append(val)
            except ValueError:
                pass
        vals = raw_vals[:n_orb]
        if sec_type == "Alpha":
            alpha_energies = vals
        elif sec_type == "Beta":
            beta_energies = vals
    _FCHK_MO_CACHE[fchk_file] = (alpha_energies, beta_energies)
    return alpha_energies, beta_energies


def get_nearest_mo(fchk_file, target_energy):
    """
    在 fchk 文件中找能量绝对值最接近的轨道（不设容差，返回最近的 N 个）。
    使用 _FCHK_MO_CACHE 避免重复读取文件。
    返回 (alpha_results, beta_results)，每个是按 |diff| 排序的列表。
    每项：{'mo_num', 'energy', 'diff'}
    """
    alpha_energies, beta_energies = _load_fchk_mo_energies(fchk_file)
    alpha_sorted = sorted([(i + 1, e, abs(e - target_energy)) for i, e in enumerate(alpha_energies)], key=lambda x: x[2])
    beta_sorted = sorted([(i + 1, e, abs(e - target_energy)) for i, e in enumerate(beta_energies)], key=lambda x: x[2])
    alpha_res = [{"mo_num": m, "energy": e, "diff": d} for m, e, d in alpha_sorted]
    beta_res = [{"mo_num": m, "energy": e, "diff": d} for m, e, d in beta_sorted]
    return alpha_res, beta_res


def get_atom_nbos(nbo_dict, atom):
    """获取涉及指定原子的所有 NBO 轨道（OR 逻辑：只需包含该原子即可）"""
    result = []
    for nbo_id, info in nbo_dict.items():
        if atom in info["atoms"]:
            result.append((nbo_id, info))
    return result


def get_nbos_grouped(nbo_dict, atom1, atom2):
    """按原子分组 NBO 轨道，区分为 A独有 / B独有 / 共享"""
    a_nbos = get_atom_nbos(nbo_dict, atom1)
    b_nbos = get_atom_nbos(nbo_dict, atom2)
    a_ids = set(n[0] for n in a_nbos)
    b_ids = set(n[0] for n in b_nbos)
    shared_ids = a_ids & b_ids
    a_only = [(nid, info) for nid, info in a_nbos if nid not in shared_ids]
    b_only = [(nid, info) for nid, info in b_nbos if nid not in shared_ids]
    shared = [(nid, info) for nid, info in a_nbos if nid in shared_ids]
    return {
        "atom1": atom1,
        "atom1_only": sorted(a_only, key=lambda x: x[0]),
        "atom2": atom2,
        "atom2_only": sorted(b_only, key=lambda x: x[0]),
        "shared": sorted(shared, key=lambda x: x[0]),
    }


def get_cross_atom_e2(e2_list, nbos_grouped, nbo_dict, min_e2):
    """筛选跨原子的 E(2) 相互作用：
    1) 供体涉及A且受体涉及B，或反之（经典跨原子）
    2) 共享 NBO（双方原子共同参与）作供体或受体 → 外部供体/受体也收入

    返回按分类排序的列表：
      category 1 = 共享 BD / BD* 直接参与（键/反键作供体或受体）
      category 2 = 其他共享 NBO 参与（LP/CR/RY）
      category 3 = 纯严格跨原子
    各组内部按 E(2) 降序
    """
    atom1 = nbos_grouped["atom1"]
    atom2 = nbos_grouped["atom2"]
    atom1_ids = set(n[0] for n in nbos_grouped["atom1_only"] + nbos_grouped["shared"])
    atom2_ids = set(n[0] for n in nbos_grouped["atom2_only"] + nbos_grouped["shared"])

    shared_nbo_ids = set(nid for nid, _ in nbos_grouped["shared"])
    shared_bond_ids = set(
        nid for nid, info in nbos_grouped["shared"]
        if info.get("type") in ("BD", "BD*")
    )

    result = []
    for e2 in e2_list:
        if e2["e2"] is None or e2["e2"] < min_e2:
            continue
        don_a = e2["donor_id"] in atom1_ids
        don_b = e2["donor_id"] in atom2_ids
        acc_a = e2["acceptor_id"] in atom1_ids
        acc_b = e2["acceptor_id"] in atom2_ids

        strict_cross = (don_a and acc_b) or (don_b and acc_a)
        shared_donor = e2["donor_id"] in shared_nbo_ids
        shared_acceptor = e2["acceptor_id"] in shared_nbo_ids
        shared_involved = shared_donor or shared_acceptor

        if not (strict_cross or shared_involved):
            continue

        bond_donor = e2["donor_id"] in shared_bond_ids
        bond_acceptor = e2["acceptor_id"] in shared_bond_ids
        if bond_donor or bond_acceptor:
            cat = 1
        elif shared_involved:
            cat = 2
        else:
            cat = 3
        result.append((cat, e2))

    result.sort(key=lambda x: (x[0], -x[1]["e2"]))
    return [e2 for _, e2 in result]


# =====================================================================
#  Multiwfn cube 生成逻辑
# =====================================================================

def gen_cube_from_mo(fchk_path, mo_number, grid_quality=2,
                      multiwfn_exe=None, work_dir=None):
    """
    调用 Multiwfn 生成指定 MO 编号的轨道波函数 cube 文件。
    mo_number: int，如 108
    返回: cube 文件路径，失败返回 None
    """
    if multiwfn_exe is None:
        multiwfn_exe = DEFAULT_MULTIWFN
    if work_dir is None:
        work_dir = os.path.dirname(os.path.abspath(fchk_path))
    os.makedirs(work_dir, exist_ok=True)

    fchk_name = os.path.basename(fchk_path)
    stem = os.path.splitext(fchk_name)[0]
    cube_name = f"{stem}_MO{mo_number}.cub"
    cube_path = os.path.join(work_dir, cube_name)

    # 如果 cube 已存在，直接返回
    if os.path.exists(cube_path):
        return cube_path


    # Multiwfn 需要在 ascii 路径下运行，先拷贝 fchk 到临时目录
    ascii_dir = os.path.join(work_dir, "_multiwfn_tmp")
    os.makedirs(ascii_dir, exist_ok=True)
    ascii_fchk = os.path.join(ascii_dir, fchk_name)
    if not os.path.exists(ascii_fchk):
        shutil.copy2(fchk_path, ascii_fchk)

    # Multiwfn 交互输入：
    #   <enter>        - 选择 fchk 文件（已在 ascii_dir 中，fchk_name 即文件名）
    #   5              - 菜单：输出波函数/密度 cube
    #   4              - 子菜单：轨道波函数
    #   <mo_number>   - 轨道编号（直接数字，如 108）
    #   <grid_quality> - 网格质量 1/2/3
    #   2              - 输出格式：cube
    #   0              - 不额外操作
    #   q              - 退出
    inputs = (
        "\n" + fchk_name + "\n5\n4\n" + str(mo_number) + "\n"
        + str(grid_quality) + "\n2\n0\nq\n"
    )

    try:
        result = subprocess.run(
            multiwfn_exe,
            input=inputs,
            capture_output=True,
            cwd=ascii_dir,
            timeout=600,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            print(f"[Multiwfn] 返回码: {result.returncode}")
            print(f"[Multiwfn] stderr: {result.stderr[:500]}")
            return None
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"[Multiwfn] 错误: {e}")
        return None

    cube_src = os.path.join(ascii_dir, "MOvalue.cub")
    if not os.path.exists(cube_src):
        print(f"[Multiwfn] MOvalue.cub 未生成，检查 Multiwfn 输出")
        print(f"[Multiwfn] stdout: {result.stdout[-500:]}")
        return None

    shutil.move(cube_src, cube_path)
    if not os.path.exists(cube_path):
        print(f"[Multiwfn] cube 移动后文件不存在: {cube_path}")
        try:
            shutil.rmtree(ascii_dir)
        except OSError:
            pass
        return None
    try:
        shutil.rmtree(ascii_dir)
    except OSError:
        pass

    return cube_path


# ══════════════════════════════════════════════════════════════
#  VMD 渲染样式 — 完整照搬 fchk_orbital.py STYLES
# ══════════════════════════════════════════════════════════════

# Element colors mapping (shared by all styles, from vcube2.0)
ATOM_COLORS_VMD = """
color Element H  101 ; color change rgb 101 0.8000 0.8000 0.8000
color Element He 102 ; color change rgb 102 0.8471 1.0000 1.0000
color Element Li 103 ; color change rgb 103 0.8000 0.4863 1.0000
color Element Be 104 ; color change rgb 104 0.8000 1.0000 0.0000
color Element B  105 ; color change rgb 105 1.0000 0.7098 0.7098
color Element C  106 ; color change rgb 106 0.5569 0.5569 0.5569
color Element N  107 ; color change rgb 107 0.0980 0.0980 0.8980
color Element O  108 ; color change rgb 108 0.8980 0.0000 0.0000
color Element F  109 ; color change rgb 109 0.6980 1.0000 1.0000
color Element Ne 110 ; color change rgb 110 0.6863 0.8863 0.9569
color Element Na 111 ; color change rgb 111 0.6667 0.3569 0.9490
color Element Mg 112 ; color change rgb 112 0.6980 0.8000 0.0000
color Element Al 113 ; color change rgb 113 0.8196 0.6471 0.6471
color Element Si 114 ; color change rgb 114 0.4980 0.6000 0.6000
color Element P  115 ; color change rgb 115 1.0000 0.4980 0.0000
color Element S  116 ; color change rgb 116 1.0000 0.7765 0.1569
color Element Cl 117 ; color change rgb 117 0.0980 0.9373 0.0980
color Element Ar 118 ; color change rgb 118 0.4980 0.8196 0.8863
color Element K  119 ; color change rgb 119 0.5569 0.2471 0.8275
color Element Ca 120 ; color change rgb 120 0.6000 0.6000 0.0000
color Element Sc 121 ; color change rgb 121 0.8980 0.8980 0.8863
color Element Ti 122 ; color change rgb 122 0.7490 0.7569 0.7765
color Element V  123 ; color change rgb 123 0.6471 0.6471 0.6667
color Element Cr 124 ; color change rgb 124 0.5373 0.6000 0.7765
color Element Mn 125 ; color change rgb 125 0.6078 0.4784 0.7765
color Element Fe 126 ; color change rgb 126 0.4980 0.4784 0.7765
color Element Co 127 ; color change rgb 127 0.3569 0.4275 1.0000
color Element Ni 128 ; color change rgb 128 0.3569 0.4784 0.7569
color Element Cu 129 ; color change rgb 129 1.0000 0.4784 0.3765
color Element Zn 130 ; color change rgb 130 0.4863 0.4980 0.6863
color Element Ga 131 ; color change rgb 131 0.7569 0.5569 0.5569
color Element Ge 132 ; color change rgb 132 0.4000 0.5569 0.5569
color Element As 133 ; color change rgb 133 0.7373 0.4980 0.8863
color Element Se 134 ; color change rgb 134 1.0000 0.6275 0.0000
color Element Br 135 ; color change rgb 135 0.6471 0.1294 0.1294
color Element Kr 136 ; color change rgb 136 0.3569 0.7294 0.8196
color Element Rb 137 ; color change rgb 137 0.4392 0.1765 0.6863
color Element Sr 138 ; color change rgb 138 0.4980 0.4000 0.0000
color Element Y  139 ; color change rgb 139 0.5765 0.9882 1.0000
color Element Zr 140 ; color change rgb 140 0.5765 0.8784 0.8784
color Element Nb 141 ; color change rgb 141 0.4471 0.7569 0.7882
color Element Mo 142 ; color change rgb 142 0.3294 0.7098 0.7098
color Element Tc 143 ; color change rgb 143 0.2275 0.6196 0.6588
color Element Ru 144 ; color change rgb 144 0.1373 0.5569 0.5882
color Element Rh 145 ; color change rgb 145 0.0392 0.4863 0.5490
color Element Pd 146 ; color change rgb 146 0.0000 0.4078 0.5176
color Element Ag 147 ; color change rgb 147 0.6000 0.7765 1.0000
color Element Cd 148 ; color change rgb 148 1.0000 0.8471 0.5569
color Element In 149 ; color change rgb 149 0.6471 0.4588 0.4471
color Element Sn 150 ; color change rgb 150 0.4000 0.4980 0.4980
color Element Sb 151 ; color change rgb 151 0.6196 0.3882 0.7098
color Element Te 152 ; color change rgb 152 0.8275 0.4784 0.0000
color Element I  153 ; color change rgb 153 0.5765 0.0000 0.5765
color Element Xe 154 ; color change rgb 154 0.2588 0.6196 0.6863
color Element Cs 155 ; color change rgb 155 0.3373 0.0863 0.5569
color Element Ba 156 ; color change rgb 156 0.4000 0.2000 0.0000
color Element La 157 ; color change rgb 157 0.4392 0.8667 1.0000
color Element Ce 158 ; color change rgb 158 1.0000 1.0000 0.7765
color Element Pr 159 ; color change rgb 159 0.8471 1.0000 0.7765
color Element Nd 160 ; color change rgb 160 0.7765 1.0000 0.7765
color Element Pm 161 ; color change rgb 161 0.6392 1.0000 0.7765
color Element Sm 162 ; color change rgb 162 0.5569 1.0000 0.7765
color Element Eu 163 ; color change rgb 163 0.3765 1.0000 0.7765
color Element Gd 164 ; color change rgb 164 0.2667 1.0000 0.7765
color Element Tb 165 ; color change rgb 165 0.1882 1.0000 0.7765
color Element Dy 166 ; color change rgb 166 0.1176 1.0000 0.7098
color Element Ho 167 ; color change rgb 167 0.0000 1.0000 0.7098
color Element Er 168 ; color change rgb 168 0.0000 0.8980 0.4588
color Element Tm 169 ; color change rgb 169 0.0000 0.8275 0.3176
color Element Yb 170 ; color change rgb 170 0.0000 0.7490 0.2196
color Element Lu 171 ; color change rgb 171 0.0000 0.6667 0.1373
color Element Hf 172 ; color change rgb 172 0.2980 0.7569 1.0000
color Element Ta 173 ; color change rgb 173 0.2980 0.6471 1.0000
color Element W  174 ; color change rgb 174 0.1490 0.5765 0.8392
color Element Re 175 ; color change rgb 175 0.1490 0.4863 0.6667
color Element Os 176 ; color change rgb 176 0.1490 0.4000 0.5882
color Element Ir 177 ; color change rgb 177 0.0863 0.3294 0.5294
color Element Pt 178 ; color change rgb 178 0.0863 0.3569 0.5569
color Element Au 179 ; color change rgb 179 1.0000 0.8196 0.1373
color Element Hg 180 ; color change rgb 180 0.7098 0.7098 0.7569
color Element Tl 181 ; color change rgb 181 0.6471 0.3294 0.2980
color Element Pb 182 ; color change rgb 182 0.3373 0.3490 0.3765
color Element Bi 183 ; color change rgb 183 0.6196 0.3098 0.7098
"""

VMD_STYLES = {
    "sob_Gold": {
        "desc": "Green-Blue, Highlight, Tan-C, Opaque/Glossy (sob original)",
        "lights": {"0": "on", "1": "on", "2": "off", "3": "on"},
        "shadows": "off", "ao": "off",
        "surface_mat": [0.1, 0.6, 1.0, 1.0, 0.0, 0.75, 0.0, 0.0, 1.0],
        "surface_mat_b": [0.1, 0.6, 1.0, 1.0, 0.0, 0.75, 0.0, 0.0, 1.0],
        "pos_color": [12, None, None],
        "neg_color": [22, None, None],
        "atom_cpk": "0.600000 0.400000 30.000000 30.000000",
        "atom_mat": [0.0, 0.65, 0.5, 0.53, 0.15, 1.0, 2.0, 0.3, 0.0],
        "c_color": "tan", "c_rgb": "0.700000 0.560000 0.360000",
        "extra_mat_lines": [
            "material change mirror Opaque 0.15",
            "material change outline Opaque 4.000000",
            "material change outlinewidth Opaque 0.5",
            "material change ambient Glossy 0.1",
            "material change diffuse Glossy 0.600000",
            "material change opacity Glossy 0.75",
            "material change shininess Glossy 1.0",
        ],
        "display_distance": "-7.0",
    },
    "sob-art": {
        "desc": "Green-Blue, Highlight, Classic (sobereva recommended)",
        "lights": {"0": "on", "1": "on", "2": "off", "3": "on"},
        "shadows": "off", "ao": "off",
        "surface_mat": [0.1, 0.6, 1.0, 1.0, 0.0, 0.75, 0.0, 0.0, 1.0],
        "surface_mat_b": [0.1, 0.6, 1.0, 1.0, 0.0, 0.75, 0.0, 0.0, 1.0],
        "pos_color": [12, None, None],
        "neg_color": [22, None, None],
        "atom_cpk": "0.600000 0.400000 30.000000 30.000000",
        "atom_mat": [0.0, 0.65, 0.5, 0.53, 0.15, 1.0, 2.0, 0.3, 0.0],
        "c_color": "tan", "c_rgb": "0.700000 0.560000 0.360000",
        "extra_mat_lines": [],
        "display_distance": "-7.0",
    },
    "ao-shiny": {
        "desc": "Orange-Cyan, Jewel-like, AO(slow)",
        "lights": {"0": "on", "1": "on", "2": "on", "3": "off"},
        "shadows": "on", "ao": "on",
        "surface_mat": [0.20, 0.8, 0.7, 0.3, 0.0, 0.7, 0.0, 0.0, 1.0],
        "surface_mat_b": [0.20, 0.8, 0.7, 0.3, 0.0, 0.7, 0.0, 0.0, 1.0],
        "pos_color": [31, 0.900, 0.500, 0.200],
        "neg_color": [32, 0.000, 0.600, 0.800],
        "atom_cpk": "0.700000 0.350000 30.000000 30.000000",
        "atom_mat": [0.0, 0.85, 0.0, 0.53, 0.0, 1.0, 0.5, 0.9, 0.0],
        "c_color": "gray", "c_rgb": "0.600000 0.600000 0.600000",
        "extra_mat_lines": [],
        "display_distance": "-7.0",
    },
    "ao-chalky": {
        "desc": "Blue-Green, Chalk-like, AO(slow)",
        "lights": {"0": "on", "1": "on", "2": "off", "3": "off"},
        "shadows": "on", "ao": "on",
        "surface_mat": [0.1, 0.85, 0.2, 0.55, 0.0, 0.8, 0.5, 0.7, 1.0],
        "surface_mat_b": [0.1, 0.85, 0.2, 0.55, 0.0, 0.8, 0.5, 0.7, 1.0],
        "pos_color": [31, 0.600, 0.900, 0.500],
        "neg_color": [32, 0.000, 0.700, 0.900],
        "atom_cpk": "0.600000 0.400000 30.000000 30.000000",
        "atom_mat": [0.0, 0.85, 0.0, 0.53, 0.0, 1.0, 0.5, 0.9, 0.0],
        "c_color": "gray", "c_rgb": "0.600000 0.600000 0.600000",
        "extra_mat_lines": [],
        "display_distance": "-7.0",
    },
    "white-green": {
        "desc": "White-Green, Plastic, Translucent",
        "lights": {"0": "on", "1": "on", "2": "off", "3": "off"},
        "shadows": "off", "ao": "off",
        "surface_mat": [0.2, 0.5, 0.6, 0.85, 0.0, 0.7, 0.6, 0.6, 1.0],
        "surface_mat_b": [0.2, 0.5, 0.6, 0.85, 0.0, 0.7, 0.6, 0.6, 1.0],
        "pos_color": [31, 0.950, 0.950, 0.950],
        "neg_color": [32, 0.500, 0.900, 0.100],
        "atom_cpk": "0.600000 0.400000 30.000000 30.000000",
        "atom_mat": [0.1, 0.5, 0.1, 0.3, 0.0, 1.0, 0.5, 0.9, 0.0],
        "c_color": "gray", "c_rgb": "0.600000 0.600000 0.600000",
        "extra_mat_lines": [],
        "display_distance": "-7.0",
    },
    "white-red": {
        "desc": "White-Red, Soft Chalk, Translucent",
        "lights": {"0": "on", "1": "on", "2": "off", "3": "off"},
        "shadows": "off", "ao": "off",
        "surface_mat": [0.2, 0.45, 0.05, 0.2, 0.0, 0.7, 0.0, 0.0, 1.0],
        "surface_mat_b": [0.2, 0.4, 0.2, 0.2, 0.0, 0.7, 0.3, 0.5, 1.0],
        "pos_color": [31, 0.950, 0.950, 0.950],
        "neg_color": [32, 1.000, 0.440, 0.260],
        "atom_cpk": "0.700000 0.350000 30.000000 30.000000",
        "atom_mat": [0.1, 0.5, 0.1, 0.3, 0.0, 1.0, 0.5, 0.9, 0.0],
        "c_color": "gray", "c_rgb": "0.600000 0.600000 0.600000",
        "extra_mat_lines": [],
        "display_distance": "-7.0",
    },
    "morandi-blue": {
        "desc": "Morandi Blue-White, Frosted Glass",
        "lights": {"0": "on", "1": "on", "2": "on", "3": "on"},
        "shadows": "off", "ao": "off",
        "surface_mat": [0.5, 0.4, 0.0, 0.0, 0.0, 0.7, 0.3, 0.3, 1.0],
        "surface_mat_b": [0.5, 0.4, 0.0, 0.0, 0.0, 0.7, 0.3, 0.3, 1.0],
        "pos_color": [31, 0.760, 0.720, 0.650],
        "neg_color": [32, 0.470, 0.490, 0.520],
        "atom_cpk": "0.700000 0.350000 30.000000 30.000000",
        "atom_mat": [0.1, 0.5, 0.1, 0.3, 0.0, 1.0, 0.5, 0.9, 0.0],
        "c_color": "gray", "c_rgb": "0.600000 0.600000 0.600000",
        "extra_mat_lines": [],
        "display_distance": "-7.0",
    },
    "morandi-green": {
        "desc": "Morandi Green-White, Frosted Glass, Opaque",
        "lights": {"0": "on", "1": "on", "2": "off", "3": "on"},
        "shadows": "off", "ao": "off",
        "surface_mat": [0.6, 0.3, 0.1, 0.2, 0.0, 1.0, 0.4, 0.6, 1.0],
        "surface_mat_b": [0.6, 0.3, 0.1, 0.2, 0.0, 1.0, 0.4, 0.6, 1.0],
        "pos_color": [31, 0.450, 0.600, 0.400],
        "neg_color": [32, 0.850, 0.800, 0.750],
        "atom_cpk": "0.600000 0.400000 30.000000 30.000000",
        "atom_mat": [0.1, 0.5, 0.1, 0.3, 0.0, 1.0, 0.5, 0.9, 0.0],
        "c_color": "gray", "c_rgb": "0.600000 0.600000 0.600000",
        "extra_mat_lines": [],
        "display_distance": "-7.0",
    },
    "morandi-orange": {
        "desc": "Morandi Orange-Blue, Frosted Glass",
        "lights": {"0": "on", "1": "on", "2": "on", "3": "on"},
        "shadows": "off", "ao": "off",
        "surface_mat": [0.5, 0.4, 0.0, 0.0, 0.0, 0.7, 0.3, 0.5, 1.0],
        "surface_mat_b": [0.5, 0.4, 0.0, 0.0, 0.0, 0.7, 0.3, 0.5, 1.0],
        "pos_color": [31, 0.760, 0.570, 0.380],
        "neg_color": [32, 0.690, 0.840, 0.890],
        "atom_cpk": "0.700000 0.350000 30.000000 30.000000",
        "atom_mat": [0.1, 0.5, 0.1, 0.3, 0.0, 1.0, 0.5, 0.9, 0.0],
        "c_color": "gray", "c_rgb": "0.600000 0.600000 0.600000",
        "extra_mat_lines": [],
        "display_distance": "-7.0",
    },
    "morandi-red": {
        "desc": "Morandi Red-White, Frosted Glass",
        "lights": {"0": "on", "1": "on", "2": "on", "3": "on"},
        "shadows": "off", "ao": "off",
        "surface_mat": [0.5, 0.4, 0.0, 0.0, 0.0, 0.7, 0.3, 0.5, 1.0],
        "surface_mat_b": [0.5, 0.4, 0.0, 0.0, 0.0, 0.7, 0.3, 0.5, 1.0],
        "pos_color": [31, 0.660, 0.410, 0.350],
        "neg_color": [32, 0.820, 0.750, 0.650],
        "atom_cpk": "0.700000 0.350000 30.000000 30.000000",
        "atom_mat": [0.1, 0.5, 0.1, 0.3, 0.0, 1.0, 0.5, 0.9, 0.0],
        "c_color": "gray", "c_rgb": "0.600000 0.600000 0.600000",
        "extra_mat_lines": [],
        "display_distance": "-7.0",
    },
    "vmwfn0": {
        "desc": "White-Ice Blue, Smooth, Translucent",
        "lights": {"0": "on", "1": "on", "2": "on", "3": "on"},
        "shadows": "off", "ao": "off",
        "surface_mat": [0.6, 0.3, 1.0, 0.95, 0.0, 0.7, 0.3, 0.3, 1.0],
        "surface_mat_b": [0.6, 0.2, 1.0, 1.0, 0.0, 0.7, 0.3, 0.3, 1.0],
        "pos_color": [31, 0.400, 0.450, 0.550],
        "neg_color": [32, 0.850, 0.820, 0.750],
        "atom_cpk": "0.700000 0.350000 30.000000 30.000000",
        "atom_mat": [0.1, 0.5, 0.1, 0.3, 0.0, 1.0, 0.5, 0.9, 0.0],
        "c_color": "gray", "c_rgb": "0.600000 0.600000 0.600000",
        "extra_mat_lines": [],
        "display_distance": "-7.0",
    },
    "vmwfn1": {
        "desc": "Red-White, Smooth Paint, Opaque",
        "lights": {"0": "on", "1": "on", "2": "off", "3": "off"},
        "shadows": "off", "ao": "off",
        "surface_mat": [0.4, 0.6, 1.0, 0.9, 0.0, 1.0, 0.4, 0.6, 1.0],
        "surface_mat_b": [0.4, 0.6, 1.0, 0.9, 0.0, 1.0, 0.4, 0.6, 1.0],
        "pos_color": [31, 0.850, 0.850, 0.750],
        "neg_color": [32, 0.600, 0.200, 0.300],
        "atom_cpk": "0.600000 0.400000 30.000000 30.000000",
        "atom_mat": [0.1, 0.5, 0.1, 0.3, 0.0, 1.0, 0.5, 0.9, 0.0],
        "c_color": "gray", "c_rgb": "0.600000 0.600000 0.600000",
        "extra_mat_lines": [],
        "display_distance": "-7.0",
    },
}

_MAT_NAMES = ["ambient", "diffuse", "specular", "shininess", "mirror", "opacity", "outline", "outlinewidth", "transmode"]

MULTI_ORBIT_COLORS = [
    {"pos": [12, None, None, None], "neg": [22, None, None, None]},
    {"pos": [31, 0.900, 0.500, 0.200], "neg": [32, 0.000, 0.600, 0.800]},
    {"pos": [33, 0.800, 0.200, 0.200], "neg": [34, 0.600, 0.200, 0.600]},
    {"pos": [35, 0.900, 0.700, 0.100], "neg": [36, 0.900, 0.300, 0.600]},
    {"pos": [37, 0.200, 0.700, 0.700], "neg": [38, 0.700, 0.500, 0.200]},
    {"pos": [39, 0.600, 0.400, 0.800], "neg": [40, 0.300, 0.700, 0.400]},
]


def launch_vmd_preview(cube_path, isovalue=0.05, vmd_exe=None,
                       tachyon_exe=None, style_name="sob-art"):
    """
    打开 VMD GUI 窗口预览 cube 文件，并启动 socket server 等待渲染指令。
    返回: (proc, render_dir, cube_path, port)，失败返回 (None, None, None, None)
    """
    if vmd_exe is None:
        vmd_exe = DEFAULT_VMD
    if tachyon_exe is None:
        tachyon_exe = DEFAULT_TACHYON

    cube_name = os.path.basename(cube_path)

    render_dir = tempfile.mkdtemp(prefix="vmd_")
    try:
        cube_path.encode("ascii")
    except UnicodeEncodeError:
        pass
    tmp_cube = os.path.join(render_dir, cube_name)
    shutil.copy2(cube_path, tmp_cube)
    cube_path = tmp_cube

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    tcl = _gen_vmd_preview_tcl(cube_name, isovalue, style_name, port)
    tcl_path = os.path.join(render_dir, "_nbo_preview.tcl")
    with open(tcl_path, "w") as f:
        f.write(tcl)

    try:
        proc = subprocess.Popen(
            [vmd_exe, "-e", "_nbo_preview.tcl"],
            cwd=render_dir,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return proc, render_dir, cube_path, port
    except FileNotFoundError as e:
        print(f"[VMD] VMD exe not found: {e}")
        return None, None, None, None


def launch_dual_vmd_preview(cube_files, isovalue=0.05, vmd_exe=None, style_name="sob-art"):
    """打开 VMD 同时预览两个轨道 cube，并启动 socket server。返回: (proc, render_dir, port)"""
    if vmd_exe is None:
        vmd_exe = DEFAULT_VMD
    if not cube_files:
        return None, None, None

    render_dir = tempfile.mkdtemp(prefix="vmd_dual_")
    copied = []
    for cp, lbl in cube_files:
        cn = os.path.basename(cp)
        tmp = os.path.join(render_dir, cn)
        shutil.copy2(cp, tmp)
        copied.append((tmp, lbl))

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    tcl = _gen_dual_orbital_tcl(copied, isovalue, style_name, port)
    tcl_path = os.path.join(render_dir, "_nbo_dual.tcl")
    with open(tcl_path, "w") as f:
        f.write(tcl)

    try:
        proc = subprocess.Popen(
            [vmd_exe, "-e", "_nbo_dual.tcl"],
            cwd=render_dir,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return proc, render_dir, port
    except FileNotFoundError as e:
        print(f"[VMD] VMD exe not found: {e}")
        return None, None, None


def _vmd_color_tcl(color_list, rep=1):
    """Generate VMD color change TCL from [ColorID, r, g, b] list. rep=1 for positive, rep=2 for negative isosurface."""
    cid = color_list[0]
    if len(color_list) >= 4 and color_list[1] is not None:
        return (f"mol modcolor {rep} top ColorID {cid}\ncolor change rgb {cid} {color_list[1]} {color_list[2]} {color_list[3]}")
    return f"mol modcolor {rep} top ColorID {cid}"


def _vmd_mat_tcl(mat_name, mat_values):
    """Generate VMD material definition TCL for a 9-element mat_values array."""
    lines = f"if {{[lsearch [material list] {mat_name}] < 0}} {{material add {mat_name}}}\n"
    for name, val in zip(_MAT_NAMES, mat_values):
        lines += f"material change {name} {mat_name} {val}\n"
    return lines


def _draw_bond_tcl():
    return r"""
# === draw_bond dashed line drawing ===
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
"""


def _gen_vmd_preview_tcl(cube_name, isovalue, style_name, port=0):
    """生成 VMD 预览 TCL 脚本（含 socket server）"""
    s = VMD_STYLES.get(style_name, VMD_STYLES["sob-art"])

    light_lines = ""
    for k, v in s["lights"].items():
        light_lines += f"light {k} {v}\n"

    shadow_lines = f"display shadows {s['shadows']}\n"
    shadow_lines += f"display ambientocclusion {s['ao']}\n"
    shadow_lines += "display aoambient 0.8\ndisplay aodirect 0.3\n"

    mat_a_tcl = _vmd_mat_tcl("_stl_a", s["surface_mat"])
    mat_b_tcl = _vmd_mat_tcl("_stl_b", s["surface_mat_b"])
    atom_mat_tcl = _vmd_mat_tcl("_stl_atom", s["atom_mat"])

    color_pos = _vmd_color_tcl(s["pos_color"])
    color_neg = _vmd_color_tcl(s["neg_color"], rep=2)

    extra_lines = s.get("extra_mat_lines", [])
    extra_tcl = "\n".join(extra_lines) + "\n" if extra_lines else ""

    return f"""{_draw_bond_tcl()}
color Display Background white
axes location Off
display depthcue off
display projection Orthographic
display rendermode GLSL

{light_lines}
{shadow_lines}

mol new {cube_name} type cube first 0 last 0 step 1 waitfor all

mol modstyle 0 top CPK {s['atom_cpk']}
mol modmaterial 0 top _stl_atom
{atom_mat_tcl}
mol modcolor 0 top Element
{ATOM_COLORS_VMD}
color Element C {s['c_color']}
color change rgb {s['c_color']} {s['c_rgb']}

mol addrep top
mol modstyle 1 top Isosurface {isovalue} 0 0 0 1 1
{color_pos}
{mat_a_tcl}
mol modmaterial 1 top _stl_a

mol addrep top
mol modstyle 2 top Isosurface -{isovalue} 0 0 0 1 1
{color_neg}
{mat_b_tcl}
mol modmaterial 2 top _stl_b

display distance {s.get('display_distance', '-8.0')}
display height 10
{extra_tcl}
puts "==========================================="
puts " VMD preview: {style_name} - {s['desc']}"
puts " +{isovalue}  -{isovalue}"
puts "==========================================="

# === Socket Server for Python commands ===
set _nbo_server [socket -server _nbo_accept -myaddr 127.0.0.1 {port}]
proc _nbo_accept {{chan addr port}} {{
    fconfigure $chan -buffering line -translation binary
    fileevent $chan readable [list _nbo_handle $chan]
}}
proc _nbo_handle {{chan}} {{
    if [eof $chan] {{
        close $chan; return
    }}
    if [catch {{gets $chan cmd}} len] {{ close $chan; return }}
    if {{$len <= 0}} return
    if [catch {{uplevel #0 $cmd}} err] {{
        puts $chan "ERROR: $err"
    }} else {{
        puts $chan "OK"
    }}
    flush $chan
}}
puts "Render server ready on port {port}"
"""


def _gen_dual_orbital_tcl(cube_files, isovalue, style_name, port=0):
    """生成双轨道 VMD 预览 TCL 脚本（含 socket server）"""
    s = VMD_STYLES.get(style_name, VMD_STYLES["sob-art"])

    light_lines = ""
    for k, v in s["lights"].items():
        light_lines += f"light {k} {v}\n"

    shadow_lines = f"display shadows {s['shadows']}\n"
    shadow_lines += f"display ambientocclusion {s['ao']}\n"
    shadow_lines += "display aoambient 0.8\ndisplay aodirect 0.3\n"

    atom_mat_tcl = _vmd_mat_tcl("_stl_atom", s["atom_mat"])

    orbital_reps = ""
    isos = isovalue if isinstance(isovalue, list) else [isovalue] * len(cube_files)
    mat_a_tcl = _vmd_mat_tcl("_stl_a", s["surface_mat"])
    mat_b_tcl = _vmd_mat_tcl("_stl_b", s["surface_mat_b"])
    for idx, (cp, orb_name) in enumerate(cube_files):
        cube_name = os.path.basename(cp)
        iso = isos[idx] if idx < len(isos) else isos[-1]
        mc = MULTI_ORBIT_COLORS[idx % len(MULTI_ORBIT_COLORS)]

        color_pos = _vmd_color_tcl(mc["pos"])
        color_neg = _vmd_color_tcl(mc["neg"], rep=2)

        orbital_reps += f"""
# Orbital {idx + 1}: {orb_name} ({cube_name})
mol new {cube_name} type cube first 0 last 0 step 1 waitfor all
mol modstyle 0 top CPK {s['atom_cpk']}
mol modmaterial 0 top _stl_atom
{atom_mat_tcl}
mol modcolor 0 top Element
{ATOM_COLORS_VMD}
color Element C {s['c_color']}
color change rgb {s['c_color']} {s['c_rgb']}

mol addrep top
mol modstyle 1 top Isosurface {iso} 0 0 0 1 1
{color_pos}
{mat_a_tcl}
mol modmaterial 1 top _stl_a

mol addrep top
mol modstyle 2 top Isosurface -{iso} 0 0 0 1 1
{color_neg}
{mat_b_tcl}
mol modmaterial 2 top _stl_b
"""

    extra_lines = s.get("extra_mat_lines", [])
    extra_tcl = "\n".join(extra_lines) + "\n" if extra_lines else ""

    orb_labels = ", ".join([lb for _, lb in cube_files])
    return f"""{_draw_bond_tcl()}
color Display Background white
axes location Off
display depthcue off
display projection Orthographic
display rendermode GLSL

{light_lines}
{shadow_lines}

{orbital_reps}

display distance {s.get('display_distance', '-8.0')}
display height 10
{extra_tcl}
puts "==========================================="
puts " VMD dual preview: {style_name} - {s['desc']}"
puts " Orbitals: {orb_labels}"
puts "==========================================="

# === Socket Server for Python commands ===
set _nbo_server [socket -server _nbo_accept -myaddr 127.0.0.1 {port}]
proc _nbo_accept {{chan addr port}} {{
    fconfigure $chan -buffering line -translation binary
    fileevent $chan readable [list _nbo_handle $chan]
}}
proc _nbo_handle {{chan}} {{
    if [eof $chan] {{
        close $chan; return
    }}
    if [catch {{gets $chan cmd}} len] {{ close $chan; return }}
    if {{$len <= 0}} return
    if [catch {{uplevel #0 $cmd}} err] {{
        puts $chan "ERROR: $err"
    }} else {{
        puts $chan "OK"
    }}
    flush $chan
}}
puts "Render server ready on port {port}"
"""


def render_current_view(port, render_dir, output_png=None,
                        tachyon_exe=None, resolution=(2000, 1500),
                        style_name="sob-art", shade_mode="full",
                        trans_raster=True, threads=4):
    """
    连接 VMD socket server，发送 render Tachyon 命令，
    然后用 Tachyon 渲染为 PNG。
    """
    if tachyon_exe is None:
        tachyon_exe = DEFAULT_TACHYON
    s = VMD_STYLES.get(style_name, VMD_STYLES.get("sob-art", {}))

    vmd_sock = None
    for attempt in range(10):
        try:
            vmd_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            vmd_sock.settimeout(3)
            vmd_sock.connect(("127.0.0.1", port))
            break
        except (ConnectionRefusedError, socket.timeout, OSError) as e:
            time.sleep(0.5)
            if vmd_sock:
                vmd_sock.close()
            vmd_sock = None

    if vmd_sock is None:
        print(f"  Cannot connect to VMD (port {port})")
        return None

    def send_cmd(cmd):
        vmd_sock.sendall((cmd + "\n").encode("utf-8"))
        time.sleep(0.5)
        resp = b""
        vmd_sock.settimeout(10)
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
        print(f"  vmdscene.dat not found: {dat}")
        return None

    shade_flag = "-fullshade" if shade_mode == "full" else "-mediumshade"
    bmp_name = "_render.bmp"
    args = [
        tachyon_exe, "vmdscene.dat",
        "-format", "BMP", "-o", bmp_name,
        "-res", str(resolution[0]), str(resolution[1]),
        "-numthreads", str(threads), "-aasamples", "24",
        shade_flag,
    ]
    if trans_raster and s.get("tachyon_options"):
        extra = s["tachyon_options"].split()
        args.extend(extra)

    try:
        result = subprocess.run(
            args, capture_output=True, cwd=render_dir, timeout=600,
            encoding="utf-8", errors="replace",
        )
        if result.returncode != 0:
            print(f"  Tachyon failed (code {result.returncode})")
            if result.stderr:
                print(f"  {result.stderr[:500]}")
            return None
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"  Tachyon error: {e}")
        return None

    bmp = os.path.join(render_dir, bmp_name)
    if not os.path.exists(bmp):
        print(f"  BMP not found: {bmp}")
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


# =====================================================================
#  run_analysis：主分析函数
# =====================================================================

# NBO 轨道类型说明（来自 NBO 7.0 官方 Table I）
NBO_TYPE_DESC = {
    "CR":    "核芯轨道 (Core) — 1中心·内层·Lewis：紧贴原子核的内层轨道",
    "LP":    "孤对电子 (Lone Pair) — 1中心·价层·Lewis：单个原子上的非键价电子对",
    "LV":    "孤对空位 (Lone Vacancy) — 1中心·价层·非Lewis：未占据的价层非键轨道",
    "LP*":   "孤对空位 (≡LV) — 非标准标签，实际即 LV 型未占据非键轨道",
    "BD":    "成键轨道 (Bond) — 2中心·价层·Lewis：两个原子间的σ共价键",
    "BD*":   "反键轨道 (Antibond) — 2中心·价层·非Lewis：对应 BD 的反键，重要受体",
    "RY*":   "Rydberg 轨道 — 1中心·Rydberg·非Lewis：超出价层的高阶轨道，占据极低",
    "3C":    "三中心键 (3-Center Bond) — 3中心·价层·Lewis：缺电子体系的多中心键",
    "3C*":   "三中心反键 (3-Center Antibond) — 3中心·价层·非Lewis：对应的反键轨道",
}

def _nbo_type_label(raw_type):
    """返回轨道类型的中文标签，如 'BD* 反键' 或 'LP 孤对'"""
    short = {
        "CR": "核芯", "LP": "孤对", "LV": "空位", "LP*": "空位",
        "BD": "成键", "BD*": "反键", "RY*": "Rydb",
        "3C": "3c键", "3C*": "3c反键",
    }
    label = short.get(raw_type, "")
    return f"{raw_type}({label})" if label else raw_type


_MO_MATCH_TOL = 0.5

def _match_nbo_to_mo(nbo_energy, fchk_file):
    """为 NBO 能量查找 fchk 中最接近的 MO，返回 (best_mo, all_matches) 或 (None, [])"""
    alpha_res, beta_res = get_nearest_mo(fchk_file, nbo_energy)
    top_alpha = [r for r in alpha_res[:3] if r["diff"] < _MO_MATCH_TOL]
    top_beta = [r for r in beta_res[:3] if r["diff"] < _MO_MATCH_TOL]
    all_matches = [("Alpha", r) for r in top_alpha] + [("Beta", r) for r in top_beta]
    all_matches.sort(key=lambda x: x[1]["diff"])
    best = all_matches[0] if all_matches else None
    return best, all_matches


def _mo_clickable(prefix, mo_type, mo_num):
    """生成可被双击识别的 MO 引用文本，格式: [Alpha MO #108]"""
    return f"{prefix}[{mo_type} MO #{mo_num}]"


def _format_nbo_line(nbo_id, info):
    """格式化单行 NBO 信息"""
    atoms_str = "-".join(f"{e}{a}" for e, a in zip(info["atom_elems"], info["atoms"]))
    occ = f"{info['occupancy']:.5f}" if info["occupancy"] is not None else " N/A"
    en = f"{info['energy']:.6f}" if info["energy"] is not None else " N/A"
    type_label = _nbo_type_label(info['type'])
    return f"NBO #{nbo_id:>4d}  {info['type']:>4s}({info['sub']})  {atoms_str:14s}  occ={occ}  E={en}  [{type_label}]"


def _format_nbo_block(nbo_id, info, fchk_file, e2_list, min_e2, nbo_dict):
    """格式化单个 NBO 的详细信息块"""
    block = []
    atoms_str = "-".join(f"{e}{a}" for e, a in zip(info["atom_elems"], info["atoms"]))
    occ = f"{info['occupancy']:.5f}" if info["occupancy"] is not None else "N/A"
    en = f"{info['energy']:.6f}" if info["energy"] is not None else "N/A"
    type_label = _nbo_type_label(info['type'])
    type_desc = NBO_TYPE_DESC.get(info['type'], '')

    block.append(f"  NBO #{nbo_id}: {info['type']}({info['sub']}) {atoms_str}  [{type_label}]")
    if type_desc:
        block.append(f"    类型: {type_desc}")
    block.append(f"    Occupancy = {occ}    Energy = {en} (Hartree)")

    if fchk_file and info["energy"] is not None:
        best, matches = _match_nbo_to_mo(info["energy"], fchk_file)
        if matches:
            block.append(f"    对应 MO:")
            for mo_type, r in matches:
                marker = " <- best" if (best and r["mo_num"] == best[1]["mo_num"] and mo_type == best[0]) else ""
                block.append(f"      {_mo_clickable('  ■ ', mo_type, r['mo_num']):40s}  E={r['energy']:.8f}  ΔE={r['diff']:.6f}{marker}")

    # E(2) 作为供体
    donor_e2 = [e for e in e2_list if e["donor_id"] == nbo_id and e["e2"] is not None and e["e2"] >= min_e2]
    donor_e2.sort(key=lambda x: x["e2"], reverse=True)
    if donor_e2:
        block.append(f"    作为供体 → ({len(donor_e2)} 条 E(2) >= {min_e2}):")
        for e2 in donor_e2[:5]:
            a_info = nbo_dict.get(e2["acceptor_id"])
            if a_info:
                a_atoms = "-".join(f"{e}{a}" for e, a in zip(a_info["atom_elems"], a_info["atoms"]))
                a_desc = f"#{e2['acceptor_id']} {a_info['type']}({a_info['sub']}){a_atoms}"
            else:
                a_desc = f"#{e2['acceptor_id']} {e2['acceptor_type_raw']}"
            block.append(f"      E(2)={e2['e2']:>7.2f}  →  {a_desc}")
        if len(donor_e2) > 5:
            block.append(f"      ... 还有 {len(donor_e2) - 5} 条 (完整列表见下方汇总)")

    # E(2) 作为受体
    acc_e2 = [e for e in e2_list if e["acceptor_id"] == nbo_id and e["e2"] is not None and e["e2"] >= min_e2]
    acc_e2.sort(key=lambda x: x["e2"], reverse=True)
    if acc_e2:
        block.append(f"    作为受体 ← ({len(acc_e2)} 条 E(2) >= {min_e2}):")
        for e2 in acc_e2[:5]:
            d_info = nbo_dict.get(e2["donor_id"])
            if d_info:
                d_atoms = "-".join(f"{e}{a}" for e, a in zip(d_info["atom_elems"], d_info["atoms"]))
                d_desc = f"#{e2['donor_id']} {d_info['type']}({d_info['sub']}){d_atoms}"
            else:
                d_desc = f"#{e2['donor_id']} {e2['donor_type_raw']}"
            block.append(f"      E(2)={e2['e2']:>7.2f}  {d_desc}  →")
        if len(acc_e2) > 5:
            block.append(f"      ... 还有 {len(acc_e2) - 5} 条 (完整列表见下方汇总)")

    return block


def tag_shared(nbo_info):
    """为共享 NBO 生成短标签：BD* / BD / LP / CR / RY 等"""
    if not nbo_info:
        return ""
    t = nbo_info.get("type", "")
    s = nbo_info.get("sub", "")
    return f"{t}({s})"


def run_analysis(log_file, atom1, atom2, min_e2, fchk_file=None):
    """
    运行完整分析，返回 (text, data_dict)
    atom2 可以传 None → 单原子模式，仅展示涉及原子1的 NBO
    """
    lines = []
    single_atom_mode = (atom2 is None or str(atom2).strip() == "")

    if single_atom_mode:
        lines.append(f"解析 log 文件: {os.path.basename(log_file)}")
        lines.append(f"查询原子 #{atom1} 的所有 NBO 轨道及其 E(2) 相互作用")
        lines.append(f"E(2) 阈值: {min_e2} kcal/mol")
    else:
        lines.append(f"解析 log 文件: {os.path.basename(log_file)}")
        lines.append(f"查询原子 #{atom1} 和 #{atom2} 的 NBO 轨道及跨原子 E(2) 相互作用")
        lines.append(f"E(2) 阈值: {min_e2} kcal/mol")
    lines.append("=" * 78)

    lines.append("\n[1/2] 解析 NBO Summary ...")
    nbo_dict = parse_nbo_summary(log_file)
    lines.append(f"  找到 {len(nbo_dict)} 个 NBO 轨道")

    lines.append("[2/2] 解析 E(2) 二阶微扰能 ...")
    e2_list = parse_e2_section(log_file)
    lines.append(f"  找到 {len(e2_list)} 条 E(2) 相互作用")

    has_fchk = bool(fchk_file and os.path.exists(fchk_file))
    if has_fchk:
        lines.append(f"\n[fchk] {os.path.basename(fchk_file)} ✓ — 预载 MO 能量...")
        _load_fchk_mo_energies(fchk_file)
    elif fchk_file:
        lines.append(f"\n[!] fchk 文件未找到: {fchk_file}")

    lines.append("\n" + "─" * 78)
    lines.append("  NBO 类型: BD=成键  BD*=反键  LP=孤对  LV=空位  CR=核芯  RY*=Rydberg  3C=三中心")
    lines.append("  [ ] 内的 MO 编号可双击打开 VMD 预览")
    lines.append("=" * 78)

    # data_dict 用于 GUI 后续操作
    data_dict = {
        "nbo_dict": nbo_dict,
        "e2_list": e2_list,
        "fchk_file": fchk_file if has_fchk else None,
        "single_atom_mode": single_atom_mode,
        "atom1": atom1,
        "atom2": atom2,
    }

    if single_atom_mode:
        # ── 单原子模式 ──
        nbos = sorted(get_atom_nbos(nbo_dict, atom1), key=lambda x: x[0])
        data_dict["nbos"] = nbos

        if not nbos:
            lines.append(f"\n>>> 未找到涉及原子 #{atom1} 的 NBO 轨道")
            lines.append("完成。")
            return "\n".join(lines), data_dict

        lines.append(f"\n{'═' * 78}")
        lines.append(f"  原子 #{atom1} 涉及的 NBO 轨道 ({len(nbos)} 个)")
        lines.append(f"     ※ 详见下方交互表格，点击行 → VMD 预览轨道")
        lines.append(f"{'═' * 78}")

        single_nbo_overview = []
        for nbo_id, info in nbos:
            entry = {
                "nbo_id": nbo_id,
                "type": info["type"],
                "sub": info["sub"],
                "atoms_str": "-".join(f"{e}{a}" for e, a in zip(info["atom_elems"], info["atoms"])),
                "occupancy": info["occupancy"],
                "energy": info["energy"],
                "type_label": _nbo_type_label(info["type"]),
                "group": "single",
                "group_label": f"#{atom1}",
            }
            if has_fchk and info["energy"] is not None:
                best, _ = _match_nbo_to_mo(info["energy"], fchk_file)
                if best:
                    entry["mo_type"] = best[0]
                    entry["mo_num"] = best[1]["mo_num"]
            single_nbo_overview.append(entry)
        data_dict["nbo_overview"] = single_nbo_overview

        for nbo_id, info in nbos:
            lines.append("")
            for blk_line in _format_nbo_block(nbo_id, info, fchk_file if has_fchk else None, e2_list, min_e2, nbo_dict):
                lines.append(blk_line)

        lines.append(f"\n{'═' * 78}")
        lines.append("完成。")
        return "\n".join(lines), data_dict

    # ── 双原子模式 ──
    grouped = get_nbos_grouped(nbo_dict, atom1, atom2)
    cross_e2 = get_cross_atom_e2(e2_list, grouped, nbo_dict, min_e2)
    data_dict["grouped"] = grouped
    data_dict["cross_e2"] = cross_e2

    total_nbos = len(grouped["atom1_only"]) + len(grouped["atom2_only"]) + len(grouped["shared"])
    if total_nbos == 0:
        lines.append(f"\n>>> 未找到涉及原子 #{atom1} 或 #{atom2} 的 NBO 轨道")
        lines.append("完成。")
        return "\n".join(lines), data_dict

    # ── 板块一：两原子的 NBO 轨道总览 ──
    lines.append(f"\n{'═' * 78}")
    lines.append(f"  一、NBO 轨道总览 — 共 {total_nbos} 个 NBO 涉及原子 #{atom1} 和/或 #{atom2}")
    lines.append(f"     ※ 详见下方交互表格，点击行 → VMD 预览轨道")
    lines.append(f"{'═' * 78}")

    nbo_overview = []
    for group_key, group_label in [("shared", f"#{atom1}↔#{atom2}"), ("atom1_only", f"仅#{atom1}"), ("atom2_only", f"仅#{atom2}")]:
        grp_nbos = grouped[group_key]
        if not grp_nbos:
            continue
        lines.append(f"\n  ▸ {group_label} ({len(grp_nbos)} 个): 见下表")
        for nbo_id, info in grp_nbos:
            entry = {
                "nbo_id": nbo_id,
                "type": info["type"],
                "sub": info["sub"],
                "atoms_str": "-".join(f"{e}{a}" for e, a in zip(info["atom_elems"], info["atoms"])),
                "occupancy": info["occupancy"],
                "energy": info["energy"],
                "type_label": _nbo_type_label(info["type"]),
                "group": group_key,
                "group_label": group_label,
            }
            if has_fchk and info["energy"] is not None:
                best, _ = _match_nbo_to_mo(info["energy"], fchk_file)
                if best:
                    entry["mo_type"] = best[0]
                    entry["mo_num"] = best[1]["mo_num"]
            nbo_overview.append(entry)
    data_dict["nbo_overview"] = nbo_overview

    # ── 板块二：NBO 详情 ──
    all_nbos = grouped["shared"] + grouped["atom1_only"] + grouped["atom2_only"]
    all_nbos.sort(key=lambda x: x[0])
    lines.append(f"\n{'═' * 78}")
    lines.append(f"  二、NBO 轨道详情 (含 E(2) 相互作用)")
    lines.append(f"{'═' * 78}")

    for nbo_id, info in all_nbos:
        lines.append("")
        for blk_line in _format_nbo_block(nbo_id, info, fchk_file if has_fchk else None, e2_list, min_e2, nbo_dict):
            lines.append(blk_line)

    # ── 板块三：跨原子 E(2) 汇总 ──
    lines.append(f"\n{'═' * 78}")
    lines.append(f"  三、跨原子 E(2) 相互作用汇总")
    lines.append(f"     (供体涉及 #{atom1} 且受体涉及 #{atom2}，或反之；含共享 NBO 参与)")
    lines.append(f"     ※ 下方表格可点击可视化")
    lines.append(f"{'═' * 78}")

    shared_nbo_ids = set(nid for nid, _ in grouped.get("shared", []))
    shared_info_map = {nid: info for nid, info in grouped.get("shared", [])}
    shared_bond_ids = set(nid for nid, info in grouped.get("shared", []) if info.get("type") in ("BD", "BD*"))

    if not cross_e2:
        lines.append(f"\n  (无 >= {min_e2} kcal/mol 的跨原子 E(2) 相互作用)")
    else:
        cat_labels = {1: ">> 键/反键直接参与", 2: ">> 其他共享 NBO 参与", 3: ">> 纯跨原子"}
        cat_counts = {1: 0, 2: 0, 3: 0}
        for e2 in cross_e2:
            bd = e2["donor_id"] in shared_bond_ids
            ba = e2["acceptor_id"] in shared_bond_ids
            sd = e2["donor_id"] in shared_nbo_ids
            sa = e2["acceptor_id"] in shared_nbo_ids
            if bd or ba:
                cat_counts[1] += 1
            elif sd or sa:
                cat_counts[2] += 1
            else:
                cat_counts[3] += 1
        parts = []
        for c in (1, 2, 3):
            if cat_counts[c]:
                parts.append(f"cat{c}={cat_counts[c]}")
        lines.append(f"\n  共 {len(cross_e2)} 条 ({', '.join(parts)}), E(2)>={min_e2} kcal/mol (详见下方交互表格)")

        cross_e2_details = []
        last_cat = 0
        global_idx = 0
        for e2 in cross_e2:
            d_info = nbo_dict.get(e2["donor_id"])
            a_info = nbo_dict.get(e2["acceptor_id"])

            if d_info:
                d_atoms = "-".join(f"{e}{a}" for e, a in zip(d_info["atom_elems"], d_info["atoms"]))
                d_str = f"#{e2['donor_id']} {d_info['type']}({d_info['sub']}){d_atoms}"
                d_type = d_info['type']
                d_label = f"{d_info['type']}({d_info['sub']}){d_atoms}"
            else:
                d_str = f"#{e2['donor_id']} {e2['donor_type_raw']}"
                d_type = e2['donor_type_raw'].rstrip('*')
                d_label = e2['donor_type_raw']

            if a_info:
                a_atoms = "-".join(f"{e}{a}" for e, a in zip(a_info["atom_elems"], a_info["atoms"]))
                a_str = f"#{e2['acceptor_id']} {a_info['type']}({a_info['sub']}){a_atoms}"
                a_type = a_info['type']
                a_label = f"{a_info['type']}({a_info['sub']}){a_atoms}"
            else:
                a_str = f"#{e2['acceptor_id']} {e2['acceptor_type_raw']}"
                a_type = e2['acceptor_type_raw'].rstrip('*')
                a_label = e2['acceptor_type_raw']

            bd = e2["donor_id"] in shared_bond_ids
            ba = e2["acceptor_id"] in shared_bond_ids
            sd = e2["donor_id"] in shared_nbo_ids
            sa = e2["acceptor_id"] in shared_nbo_ids
            if bd or ba:
                cat = 1
            elif sd or sa:
                cat = 2
            else:
                cat = 3

            if cat != last_cat:
                lines.append(f"\n  {cat_labels[cat]} ({cat_counts[cat]} 条):")
                last_cat = cat

            global_idx += 1
            stars = "★★★" if e2["e2"] >= 10 else ("★★" if e2["e2"] >= 2 else ("★" if e2["e2"] >= 0.5 else "  "))
            shared_tag = ""
            don_is_shared = e2["donor_id"] in shared_nbo_ids
            acc_is_shared = e2["acceptor_id"] in shared_nbo_ids
            if don_is_shared and acc_is_shared:
                s_don = shared_info_map.get(e2["donor_id"], {})
                s_acc = shared_info_map.get(e2["acceptor_id"], {})
                shared_tag = f" [共{tag_shared(s_don)}{tag_shared(s_acc)}]"
            elif don_is_shared:
                s_don = shared_info_map.get(e2["donor_id"], {})
                shared_tag = f" [共{tag_shared(s_don)}供体]"
            elif acc_is_shared:
                s_acc = shared_info_map.get(e2["acceptor_id"], {})
                shared_tag = f" [共{tag_shared(s_acc)}受体]"
            lines.append(f"  {global_idx:>3d}. E(2)={e2['e2']:>7.2f}  {stars}  {d_str}  →  {a_str}{shared_tag}")

            detail = {
                "idx": global_idx,
                "cat": cat,
                "e2": e2["e2"],
                "stars": stars,
                "donor_id": e2["donor_id"],
                "donor_str": d_str,
                "donor_label": d_label,
                "acceptor_id": e2["acceptor_id"],
                "acceptor_str": a_str,
                "acceptor_label": a_label,
                "d_info": d_info,
                "a_info": a_info,
                "shared_tag": shared_tag,
                "don_is_shared": don_is_shared,
                "acc_is_shared": acc_is_shared,
            }
            if has_fchk:
                d_matches = _match_nbo_to_mo(d_info["energy"], fchk_file) if (d_info and d_info.get("energy") is not None) else []
                a_matches = _match_nbo_to_mo(a_info["energy"], fchk_file) if (a_info and a_info.get("energy") is not None) else []
                d_best = d_matches[0] if d_matches else None
                a_best = a_matches[0] if a_matches else None
                if d_best and a_best:
                    detail["mo1_type"] = d_best[0]
                    detail["mo1_num"] = d_best[1]["mo_num"]
                    detail["mo2_type"] = a_best[0]
                    detail["mo2_num"] = a_best[1]["mo_num"]
                elif d_best:
                    detail["mo1_type"] = d_best[0]
                    detail["mo1_num"] = d_best[1]["mo_num"]
                elif a_best:
                    detail["mo1_type"] = a_best[0]
                    detail["mo1_num"] = a_best[1]["mo_num"]
            cross_e2_details.append(detail)
        data_dict["cross_e2_details"] = cross_e2_details

    lines.append(f"\n{'═' * 78}")
    lines.append("完成。")
    return "\n".join(lines), data_dict


# =====================================================================
#  GUI 部分

# CPK Atomic Colors - from gxtb_gui.py
CPK_COLORS = {
    "H": "#FFFFFF", "He": "#D9FFFF", "Li": "#CC80FF", "Be": "#C2FF00",
    "B": "#FFB5B5", "C": "#909090", "N": "#3050F8", "O": "#FF0D0D",
    "F": "#90E050", "Ne": "#B3E3F5", "Na": "#AB5CF2", "Mg": "#8AFF00",
    "Al": "#BFA6A6", "Si": "#F0C8A0", "P": "#FF8000", "S": "#FFFF30",
    "Cl": "#1FF01F", "Ar": "#80D1E3", "K": "#8F40D4", "Ca": "#3DFF00",
    "Sc": "#E6E6E6", "Ti": "#BFC2C7", "V": "#A6A6AB", "Cr": "#8A99C7",
    "Mn": "#9C7AC7", "Fe": "#E06633", "Co": "#F090A0", "Ni": "#50D050",
    "Cu": "#C88033", "Zn": "#7D80B0", "Ga": "#C28F8F", "Ge": "#668F8F",
    "As": "#BD80E3", "Se": "#FFA100", "Br": "#A62929", "Kr": "#5CB8D1",
    "Rb": "#702EB0", "Sr": "#00FF00", "Y": "#94FFFF", "Zr": "#94E0E0",
    "Nb": "#73C2C9", "Mo": "#54B5B5", "Tc": "#3B9E9E", "Ru": "#248F8F",
    "Rh": "#0A7D8C", "Pd": "#006985", "Ag": "#C0C0C0", "Cd": "#FFD98F",
    "In": "#A67573", "Sn": "#668080", "Sb": "#9E63B5", "Te": "#D47A00",
    "I": "#940094", "Xe": "#429EB0", "Cs": "#57178F", "Ba": "#00C900",
    "La": "#70D4FF", "Ce": "#FFFFC7", "Pr": "#D9FFC7", "Nd": "#C7FFC7",
    "Pm": "#A3FFC7", "Sm": "#8FFFC7", "Eu": "#61FFC7", "Gd": "#45FFC7",
    "Tb": "#30FFC7", "Dy": "#1FFFC7", "Ho": "#00FF9C", "Er": "#00E675",
    "Tm": "#00D451", "Yb": "#00BF38", "Lu": "#00AB24", "Hf": "#4DC2FF",
    "Ta": "#4DA6FF", "W": "#2194D6", "Re": "#267DAB", "Os": "#266696",
    "Ir": "#175487", "Pt": "#D0D0E0", "Au": "#FFD123", "Hg": "#B8B8D2",
    "Tl": "#A55443", "Pb": "#575961", "Bi": "#9E4FB5", "Po": "#AB5C00",
    "At": "#754F45", "Rn": "#428296", "Fr": "#420066", "Ra": "#007D00",
    "Ac": "#70ABFA", "Th": "#00BAFF", "Pa": "#00A1FF", "U": "#008FFF",
    "Np": "#0080FF", "Pu": "#006BFF", "Am": "#545CF2", "Cm": "#785CE3",
}

# Covalent Radii for visualization
_COVALENT_RADII_VIZ = {
    "H": 0.31, "He": 0.28, "Li": 1.28, "Be": 0.96, "B": 0.84,
    "C": 0.76, "N": 0.71, "O": 0.66, "F": 0.57, "Ne": 0.58,
    "Na": 1.66, "Mg": 1.41, "Al": 1.21, "Si": 1.11, "P": 1.07,
    "S": 1.05, "Cl": 1.02, "Ar": 1.06, "K": 2.03, "Ca": 1.76,
    "Sc": 1.70, "Ti": 1.60, "V": 1.53, "Cr": 1.39, "Mn": 1.39,
    "Fe": 1.32, "Co": 1.26, "Ni": 1.24, "Cu": 1.32, "Zn": 1.22,
    "Ga": 1.22, "Ge": 1.20, "As": 1.19, "Se": 1.20, "Br": 1.20,
    "Kr": 1.16, "Rb": 2.20, "Sr": 1.95, "Y": 1.90, "Zr": 1.75,
    "Nb": 1.64, "Mo": 1.54, "Tc": 1.47, "Ru": 1.46, "Rh": 1.42,
    "Pd": 1.39, "Ag": 1.45, "Cd": 1.44, "In": 1.42, "Sn": 1.39,
    "Sb": 1.39, "Te": 1.38, "I": 1.39, "Xe": 1.40, "Cs": 2.44,
    "Ba": 2.15, "La": 2.07, "Ce": 2.04, "Pr": 2.03, "Nd": 2.01,
    "Pm": 1.99, "Sm": 1.98, "Eu": 1.98, "Gd": 1.96, "Tb": 1.94,
    "Dy": 1.92, "Ho": 1.92, "Er": 1.89, "Tm": 1.90, "Yb": 1.87,
    "Lu": 1.87, "Hf": 1.75, "Ta": 1.70, "W": 1.62, "Re": 1.51,
    "Os": 1.44, "Ir": 1.41, "Pt": 1.36, "Au": 1.36, "Hg": 1.32,
    "Tl": 1.45, "Pb": 1.46, "Bi": 1.48, "Po": 1.40, "At": 1.50,
    "Rn": 1.50, "Fr": 2.60, "Ra": 2.21, "Ac": 2.15, "Th": 2.06,
    "Pa": 2.00, "U": 1.96, "Np": 1.90, "Pu": 1.87, "Am": 1.80,
    "Cm": 1.69,
}




class WorkerSignals(QObject):
    append_text = pyqtSignal(str)
    analysis_done = pyqtSignal(str, dict)
    analysis_error = pyqtSignal(str)
    vmd_ready = pyqtSignal(int)
    vmd_error = pyqtSignal(str)


class MoleculeViewer(QWidget):
    atom_selected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._atoms = []
        self._bonds = []
        self._highlight_atoms = set()
        self._label_mode = "index"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._plotter = QtInteractor(self)
        layout.addWidget(self._plotter)

        self._plotter.set_background("#FFFFFF")
        self._plotter.enable_eye_dome_lighting()

        self._plotter.iren.add_observer("LeftButtonPressEvent", self._on_click)

    def load_molecule(self, atoms, bonds):
        self._atoms = atoms
        self._bonds = bonds or []
        self._highlight_atoms = set()
        self._plotter.clear()
        self._plotter.enable_eye_dome_lighting()
        self._draw_bonds()
        self._draw_atoms()
        self._draw_labels()
        self._plotter.reset_camera()
        self._plotter.render()

    def _draw_atoms(self):
        scale_factor = 0.30
        base_sphere = pv.Sphere(radius=1.0, theta_resolution=20, phi_resolution=20)
        pts = []
        colors = []
        radii = []
        for atom in self._atoms:
            idx = atom['idx']
            elem = atom['elem']
            pos = np.array([atom['x'], atom['y'], atom['z']], dtype=float)
            radius = _COVALENT_RADII_VIZ.get(elem, 1.5) * scale_factor
            radius = max(0.05, min(radius, 0.6))
            color = CPK_COLORS.get(elem, "#FF69B4")
            pts.append(pos)
            colors.append(color)
            radii.append(radius)

        for i, (pos, color, r) in enumerate(zip(pts, colors, radii)):
            mesh = base_sphere.copy()
            mesh.scale(r, inplace=True)
            mesh.translate(pos, inplace=True)
            self._plotter.add_mesh(
                mesh, color=color, smooth_shading=True,
                pbr=True, metallic=0.05, roughness=0.4,
                diffuse=0.9, specular=0.6, specular_power=30,
                render=False,
                name=f"atom_{self._atoms[i]['idx']}"
            )

        if pts:
            pc = pv.PolyData(np.array(pts, dtype=float))
            pc["atom_id"] = np.array([a['idx'] for a in self._atoms])
            self._point_cloud = pc

    def _draw_bonds(self):
        for i1, i2 in self._bonds:
            a1 = next((a for a in self._atoms if a['idx'] == i1), None)
            a2 = next((a for a in self._atoms if a['idx'] == i2), None)
            if not a1 or not a2:
                continue
            p1 = np.array([a1['x'], a1['y'], a1['z']], dtype=float)
            p2 = np.array([a2['x'], a2['y'], a2['z']], dtype=float)
            mid = (p1 + p2) / 2.0
            c1 = CPK_COLORS.get(a1['elem'], "#909090")
            c2 = CPK_COLORS.get(a2['elem'], "#909090")
            cyl1 = pv.Cylinder(center=(p1 + mid) / 2.0,
                               direction=mid - p1,
                               radius=0.08,
                               height=np.linalg.norm(mid - p1),
                               resolution=8)
            self._plotter.add_mesh(cyl1, color=c1, smooth_shading=True,
                                   pbr=True, metallic=0.05, roughness=0.5,
                                   render=False)
            cyl2 = pv.Cylinder(center=(mid + p2) / 2.0,
                               direction=p2 - mid,
                               radius=0.08,
                               height=np.linalg.norm(p2 - mid),
                               resolution=8)
            self._plotter.add_mesh(cyl2, color=c2, smooth_shading=True,
                                   pbr=True, metallic=0.05, roughness=0.5,
                                   render=False)

    def _draw_labels(self):
        if self._label_mode == "none":
            return
        pts = np.array([[a['x'], a['y'], a['z']] for a in self._atoms], dtype=float)
        if self._label_mode == "index":
            labels = [str(a['idx']) for a in self._atoms]
        elif self._label_mode == "element":
            labels = [a['elem'] for a in self._atoms]
        else:
            labels = [f"{a['elem']}{a['idx']}" for a in self._atoms]
        self._plotter.add_point_labels(
            pv.PolyData(pts), labels,
            font_size=14, text_color="#333333",
            point_size=1, shape=None,
            always_visible=True, name="atom_labels"
        )

    def set_highlight_atoms(self, indices):
        self._highlight_atoms = set(indices)

    def set_label_mode(self, mode):
        self._label_mode = mode
        self._redraw_labels()

    def _redraw_labels(self):
        self._plotter.remove_actor("atom_labels")
        self._draw_labels()

    def reset_view(self):
        self._plotter.reset_camera()

    def _on_click(self, obj, event):
        if not hasattr(self, '_point_cloud'):
            return
        picker = self._plotter.iren.get_picker()
        if picker and hasattr(picker, 'GetPickPosition'):
            pos = picker.GetPickPosition()
            if pos is not None:
                for atom in self._atoms:
                    ap = np.array([atom['x'], atom['y'], atom['z']])
                    if np.linalg.norm(np.array(pos) - ap) < 0.3:
                        self.atom_selected.emit(atom['idx'])
                        return


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NBO E(2) 分析 + 轨道可视化 v3.0")
        self.setGeometry(100, 100, 1400, 900)

        paths = load_config()
        self.multiwfn_path = paths["multiwfn"]
        self.vmd_path = paths["vmd"]
        self.tachyon_path = paths["tachyon"]

        self._atoms = []
        self._bonds = []
        self._last_result = None
        self._analysis_data = None
        self._nbo_overview_data = []
        self._cross_e2_details = []

        self.vmd_proc = None
        self.vmd_render_dir = None
        self.vmd_port = None
        self.current_iso = 0.05
        self.current_opacity = None
        self._vmd_persist_sock = None

        self._build_menubar()
        self._build_ui()
        self._build_statusbar()

    def _build_menubar(self):
        mb = self.menuBar()

        file_menu = mb.addMenu("文件(&F)")
        open_log = QAction("打开日志文件...", self)
        open_log.triggered.connect(self._browse_log)
        file_menu.addAction(open_log)
        open_fchk = QAction("打开 fchk 文件...", self)
        open_fchk.triggered.connect(self._browse_fchk)
        file_menu.addAction(open_fchk)
        file_menu.addSeparator()
        quit_act = QAction("退出", self)
        quit_act.triggered.connect(self.close)
        file_menu.addAction(quit_act)

        settings_menu = mb.addMenu("设置(&S)")
        settings_act = QAction("设置路径...", self)
        settings_act.triggered.connect(self._open_settings)
        settings_menu.addAction(settings_act)
        save_paths_act = QAction("保存路径", self)
        save_paths_act.triggered.connect(self._save_paths_now)
        settings_menu.addAction(save_paths_act)

    def _build_statusbar(self):
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("就绪：请选择日志文件")

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_splitter = QSplitter(Qt.Horizontal)

        left_tabs = QTabWidget()
        main_splitter.addWidget(left_tabs)

        analysis_tab = QWidget()
        vmd_tab = QWidget()
        left_tabs.addTab(analysis_tab, "分析")
        left_tabs.addTab(vmd_tab, "VMD 工具")

        self._build_analysis_tab(analysis_tab)
        self._build_vmd_tab(vmd_tab)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # ── 右侧纵向分屏: 上半(预览+日志) | 下半(NBO+E2) ──
        v_splitter = QSplitter(Qt.Vertical)

        # ── 上半: 横向分屏 ──
        top_splitter = QSplitter(Qt.Horizontal)

        viewer_grp = QGroupBox("分子预览")
        viewer_layout = QVBoxLayout(viewer_grp)
        viewer_toolbar = QHBoxLayout()
        self._atom_info_label = QLabel("原子: --")
        viewer_toolbar.addWidget(self._atom_info_label)
        viewer_toolbar.addStretch()
        viewer_toolbar.addWidget(QLabel("标签:"))
        self._label_mode_combo = QComboBox()
        self._label_mode_combo.addItems(["编号", "元素", "元素+编号", "无"])
        self._label_mode_combo.currentTextChanged.connect(self._on_label_mode_changed)
        viewer_toolbar.addWidget(self._label_mode_combo)
        reset_btn = QPushButton("重置视角")
        reset_btn.clicked.connect(self._on_reset_view)
        viewer_toolbar.addWidget(reset_btn)
        viewer_layout.addLayout(viewer_toolbar)
        self._viewer = MoleculeViewer()
        self._viewer.atom_selected.connect(self._on_atom_selected)
        viewer_layout.addWidget(self._viewer, 1)
        top_splitter.addWidget(viewer_grp)

        log_grp = QGroupBox("运行日志")
        log_layout = QVBoxLayout(log_grp)
        self._result_text = QTextEdit()
        self._result_text.setReadOnly(True)
        self._result_text.setFont(QFont("Consolas", 10))
        self._result_text.setStyleSheet("QTextEdit { background-color: #fafbfc; }")
        self._result_text.mouseDoubleClickEvent = self._on_result_dclick
        log_layout.addWidget(self._result_text)
        top_splitter.addWidget(log_grp)

        top_splitter.setSizes([600, 600])
        v_splitter.addWidget(top_splitter)

        # ── 下半: 横向分屏 ──
        bottom_splitter = QSplitter(Qt.Horizontal)

        nbo_grp = QGroupBox("NBO 总览")
        nbo_layout = QVBoxLayout(nbo_grp)
        self._nbo_table = QTableWidget(0, 6)
        self._nbo_table.setHorizontalHeaderLabels(
            ["NBO编号", "类型", "原子", "占据数", "能量", "分组"]
        )
        nbo_header = self._nbo_table.horizontalHeader()
        nbo_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        nbo_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        nbo_header.setSectionResizeMode(2, QHeaderView.Stretch)
        nbo_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        nbo_header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        nbo_header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self._nbo_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._nbo_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._nbo_table.setAlternatingRowColors(True)
        self._nbo_table.cellDoubleClicked.connect(self._on_nbo_table_dclick)
        nbo_layout.addWidget(self._nbo_table)
        bottom_splitter.addWidget(nbo_grp)

        e2_grp = QGroupBox("E(2) 相互作用")
        e2_layout = QVBoxLayout(e2_grp)
        self._e2_table = QTableWidget(0, 7)
        self._e2_table.setHorizontalHeaderLabels(
            ["序号", "E(2)", "供体", "受体", "分类", "星级", "共享"]
        )
        e2_header = self._e2_table.horizontalHeader()
        e2_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        e2_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        e2_header.setSectionResizeMode(2, QHeaderView.Stretch)
        e2_header.setSectionResizeMode(3, QHeaderView.Stretch)
        e2_header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        e2_header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        e2_header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self._e2_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._e2_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._e2_table.setAlternatingRowColors(True)
        self._e2_table.cellDoubleClicked.connect(self._on_e2_table_dclick)
        e2_layout.addWidget(self._e2_table)
        bottom_splitter.addWidget(e2_grp)

        bottom_splitter.setSizes([600, 600])
        v_splitter.addWidget(bottom_splitter)

        v_splitter.setSizes([500, 500])
        right_layout.addWidget(v_splitter)

        main_splitter.addWidget(right_panel)
        main_splitter.setStretchFactor(0, 0)
        main_splitter.setStretchFactor(1, 1)
        main_splitter.setSizes([420, 980])

        main_layout.addWidget(main_splitter)

    def _build_analysis_tab(self, tab):
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        file_grp = QGroupBox("文件")
        file_layout = QGridLayout(file_grp)
        file_layout.addWidget(QLabel("日志文件:"), 0, 0)
        self._log_edit = QLineEdit()
        file_layout.addWidget(self._log_edit, 0, 1)
        log_btn = QPushButton("浏览...")
        log_btn.clicked.connect(self._browse_log)
        file_layout.addWidget(log_btn, 0, 2)
        file_layout.addWidget(QLabel("fchk 文件:"), 1, 0)
        self._fchk_edit = QLineEdit()
        file_layout.addWidget(self._fchk_edit, 1, 1)
        fchk_btn = QPushButton("浏览...")
        fchk_btn.clicked.connect(self._browse_fchk)
        file_layout.addWidget(fchk_btn, 1, 2)
        layout.addWidget(file_grp)

        params_grp = QGroupBox("分析参数")
        params_layout = QGridLayout(params_grp)
        params_layout.addWidget(QLabel("原子 1:"), 0, 0)
        self._atom1_spin = QSpinBox()
        self._atom1_spin.setMinimum(1)
        self._atom1_spin.setMaximum(9999)
        params_layout.addWidget(self._atom1_spin, 0, 1)
        params_layout.addWidget(QLabel("原子 2:"), 0, 2)
        self._atom2_spin = QSpinBox()
        self._atom2_spin.setMinimum(0)
        self._atom2_spin.setMaximum(9999)
        self._atom2_spin.setSpecialValueText("--")
        params_layout.addWidget(self._atom2_spin, 0, 3)
        params_layout.addWidget(QLabel("E(2) 阈值:"), 1, 0)
        self._min_e2_spin = QDoubleSpinBox()
        self._min_e2_spin.setValue(0.5)
        self._min_e2_spin.setDecimals(2)
        self._min_e2_spin.setSingleStep(0.1)
        params_layout.addWidget(self._min_e2_spin, 1, 1)
        params_layout.addWidget(QLabel("等值面:"), 1, 2)
        self._isovalue_edit = QLineEdit("0.05")
        params_layout.addWidget(self._isovalue_edit, 1, 3)
        layout.addWidget(params_grp)

        render_grp = QGroupBox("渲染参数")
        render_layout = QGridLayout(render_grp)
        render_layout.addWidget(QLabel("样式:"), 0, 0)
        self._style_combo = QComboBox()
        self._style_combo.addItems(list(VMD_STYLES.keys()))
        self._style_combo.setCurrentText("sob-art")
        render_layout.addWidget(self._style_combo, 0, 1)
        render_layout.addWidget(QLabel("网格:"), 0, 2)
        self._grid_combo = QComboBox()
        self._grid_combo.addItems(["1", "2", "3"])
        self._grid_combo.setCurrentText("2")
        render_layout.addWidget(self._grid_combo, 0, 3)
        render_layout.addWidget(QLabel("分辨率:"), 1, 0)
        self._res_combo = QComboBox()
        self._res_combo.addItems(["2000x1500", "1200x900", "3000x2250"])
        render_layout.addWidget(self._res_combo, 1, 1)
        render_layout.addWidget(QLabel("着色:"), 1, 2)
        self._shade_combo = QComboBox()
        self._shade_combo.addItems(["full", "medium"])
        render_layout.addWidget(self._shade_combo, 1, 3)
        render_layout.addWidget(QLabel("透光栅:"), 2, 0)
        self._trans_check = QCheckBox()
        self._trans_check.setChecked(True)
        render_layout.addWidget(self._trans_check, 2, 1)
        render_layout.addWidget(QLabel("线程数:"), 2, 2)
        self._threads_combo = QComboBox()
        self._threads_combo.addItems(["1", "2", "4", "8"])
        self._threads_combo.setCurrentText("4")
        render_layout.addWidget(self._threads_combo, 2, 3)
        layout.addWidget(render_grp)

        live_grp = QGroupBox("实时调节 (VMD 打开后可用)")
        live_layout = QGridLayout(live_grp)
        live_layout.addWidget(QLabel("Isovalue:"), 0, 0)
        self._iso_slider = QSlider(Qt.Horizontal)
        self._iso_slider.setRange(5, 500)
        self._iso_slider.setValue(50)
        self._iso_slider.setEnabled(False)
        self._iso_slider.valueChanged.connect(self._on_iso_changed)
        live_layout.addWidget(self._iso_slider, 0, 1)
        self._iso_value_label = QLabel("0.050")
        live_layout.addWidget(self._iso_value_label, 0, 2)
        live_layout.addWidget(QLabel("Opacity:"), 1, 0)
        self._opacity_slider = QSlider(Qt.Horizontal)
        self._opacity_slider.setRange(5, 100)
        self._opacity_slider.setValue(75)
        self._opacity_slider.setEnabled(False)
        self._opacity_slider.valueChanged.connect(self._on_opacity_changed)
        live_layout.addWidget(self._opacity_slider, 1, 1)
        self._opacity_value_label = QLabel("0.75")
        live_layout.addWidget(self._opacity_value_label, 1, 2)
        layout.addWidget(live_grp)

        btn_bar = QHBoxLayout()
        self._start_btn = QPushButton("开始分析")
        self._start_btn.clicked.connect(self._on_start_analysis)
        btn_bar.addWidget(self._start_btn)
        self._save_btn = QPushButton("保存结果")
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self._on_save)
        btn_bar.addWidget(self._save_btn)
        self._copy_btn = QPushButton("复制全部")
        self._copy_btn.setEnabled(False)
        self._copy_btn.clicked.connect(self._on_copy)
        btn_bar.addWidget(self._copy_btn)
        self._render_btn = QPushButton("渲染图片")
        self._render_btn.setEnabled(False)
        self._render_btn.clicked.connect(self._on_render)
        btn_bar.addWidget(self._render_btn)
        self._close_vmd_btn = QPushButton("关闭 VMD")
        self._close_vmd_btn.setEnabled(False)
        self._close_vmd_btn.clicked.connect(self._close_vmd)
        btn_bar.addWidget(self._close_vmd_btn)
        layout.addLayout(btn_bar)

    def _build_vmd_tab(self, tab):
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        tools_grp = QGroupBox("外部工具路径")
        tools_layout = QFormLayout(tools_grp)
        self._var_multiwfn = QLineEdit(self.multiwfn_path)
        tools_layout.addRow("MultiWFN 路径:", self._var_multiwfn)
        mw_btn = QPushButton("浏览...")
        mw_btn.clicked.connect(lambda: self._browse_tool(self._var_multiwfn))
        tools_layout.addRow("", mw_btn)
        self._var_vmd = QLineEdit(self.vmd_path)
        tools_layout.addRow("VMD 路径:", self._var_vmd)
        vmd_btn = QPushButton("浏览...")
        vmd_btn.clicked.connect(lambda: self._browse_tool(self._var_vmd))
        tools_layout.addRow("", vmd_btn)
        self._var_tachyon = QLineEdit(self.tachyon_path)
        tools_layout.addRow("Tachyon 路径:", self._var_tachyon)
        tach_btn = QPushButton("浏览...")
        tach_btn.clicked.connect(lambda: self._browse_tool(self._var_tachyon))
        tools_layout.addRow("", tach_btn)
        save_btn = QPushButton("保存工具路径")
        save_btn.clicked.connect(self._save_tool_paths)
        tools_layout.addRow(save_btn)
        layout.addWidget(tools_grp)

        hfilter_grp = QGroupBox("隐藏氢原子")
        hfilter_layout = QHBoxLayout(hfilter_grp)
        self._h_indices_edit = QLineEdit()
        self._h_indices_edit.setPlaceholderText("保留的氢原子编号 (如: 1,2,3)")
        hfilter_layout.addWidget(self._h_indices_edit)
        self._h_filter_btn = QPushButton("隐藏氢")
        self._h_filter_btn.setEnabled(False)
        self._h_filter_btn.clicked.connect(self._toggle_h_filter)
        hfilter_layout.addWidget(self._h_filter_btn)
        layout.addWidget(hfilter_grp)

        bond_grp = QGroupBox("绘制虚线键")
        bond_layout = QGridLayout(bond_grp)
        bond_layout.addWidget(QLabel("原子 1:"), 0, 0)
        self._bond_a1 = QSpinBox()
        self._bond_a1.setMinimum(1)
        self._bond_a1.setMaximum(9999)
        bond_layout.addWidget(self._bond_a1, 0, 1)
        bond_layout.addWidget(QLabel("原子 2:"), 0, 2)
        self._bond_a2 = QSpinBox()
        self._bond_a2.setMinimum(1)
        self._bond_a2.setMaximum(9999)
        bond_layout.addWidget(self._bond_a2, 0, 3)
        bond_layout.addWidget(QLabel("类型:"), 1, 0)
        self._bond_type = QComboBox()
        self._bond_type.addItems(["pymol", "cylinder", "dots", "sphere", "cone", "line"])
        bond_layout.addWidget(self._bond_type, 1, 1)
        bond_layout.addWidget(QLabel("颜色:"), 1, 2)
        self._bond_color = QComboBox()
        self._bond_color.addItems(["cyan", "yellow", "green", "red", "blue", "orange", "white", "gray"])
        bond_layout.addWidget(self._bond_color, 1, 3)
        btn_row = QHBoxLayout()
        self._draw_bond_btn = QPushButton("绘制")
        self._draw_bond_btn.setEnabled(False)
        self._draw_bond_btn.clicked.connect(self._draw_bond)
        btn_row.addWidget(self._draw_bond_btn)
        self._undo_bond_btn = QPushButton("撤销")
        self._undo_bond_btn.setEnabled(False)
        self._undo_bond_btn.clicked.connect(self._undo_bond)
        btn_row.addWidget(self._undo_bond_btn)
        self._clear_bond_btn = QPushButton("清除")
        self._clear_bond_btn.setEnabled(False)
        self._clear_bond_btn.clicked.connect(self._clear_bond)
        btn_row.addWidget(self._clear_bond_btn)
        bond_layout.addLayout(btn_row, 2, 0, 1, 4)
        layout.addWidget(bond_grp)

        render_grp = QGroupBox("渲染图片")
        render_layout = QHBoxLayout(render_grp)
        render_layout.addWidget(QLabel("分辨率:"))
        self._vmd_res_combo = QComboBox()
        self._vmd_res_combo.addItems(["2000x1500", "1200x900", "3000x2250"])
        render_layout.addWidget(self._vmd_res_combo)
        self._vmd_render_btn = QPushButton("渲染")
        self._vmd_render_btn.setEnabled(False)
        self._vmd_render_btn.clicked.connect(self._on_render)
        render_layout.addWidget(self._vmd_render_btn)
        layout.addWidget(render_grp)
        layout.addStretch()

    def _browse_tool(self, line_edit):
        path, _ = QFileDialog.getOpenFileName(self, "Select Executable")
        if path:
            line_edit.setText(path)

    def _save_tool_paths(self):
        self.multiwfn_path = self._var_multiwfn.text()
        self.vmd_path = self._var_vmd.text()
        self.tachyon_path = self._var_tachyon.text()
        save_config(self.multiwfn_path, self.vmd_path, self.tachyon_path)
        self._status_bar.showMessage("工具路径已保存")
        QMessageBox.information(self, "已保存", "工具路径保存成功")

    def _browse_log(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select NBO log file", "", "Log files (*.log *.out);;All files (*.*)"
        )
        if not path:
            return
        self._log_edit.setText(path)
        self._status_bar.showMessage("正在加载分子结构...")

        atoms = parse_log_atoms(path)
        if not atoms:
            self._status_bar.showMessage("无法从日志文件中解析原子坐标")
            return

        bonds = calculate_bonds(atoms)
        self._atoms = atoms
        self._bonds = bonds
        self._viewer.load_molecule(atoms, bonds)
        self._atom1_spin.setMaximum(len(atoms))
        self._atom2_spin.setMaximum(len(atoms))
        self._bond_a1.setMaximum(len(atoms))
        self._bond_a2.setMaximum(len(atoms))
        self._status_bar.showMessage(f"已加载 {len(atoms)} 个原子, {len(bonds)} 个化学键（来自日志文件）")

        log_dir = os.path.dirname(os.path.abspath(path))
        log_stem = os.path.splitext(os.path.basename(path))[0]
        for ext in [".fchk", ".fch"]:
            candidate = os.path.join(log_dir, log_stem + ext)
            if os.path.exists(candidate):
                self._fchk_edit.setText(candidate)
                self._status_bar.showMessage(
                    f"已加载 {len(atoms)} 个原子，自动检测到 fchk: {os.path.basename(candidate)}"
                )
                break

    def _browse_fchk(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select fchk file", "", "fchk files (*.fchk *.fch);;All files (*.*)"
        )
        if not path:
            return
        self._fchk_edit.setText(path)
        self._status_bar.showMessage("正在从 fchk 文件加载分子结构...")

        atoms = parse_fchk_atoms(path)
        if not atoms:
            self._status_bar.showMessage("无法从 fchk 文件中解析原子坐标")
            return

        bonds = calculate_bonds(atoms)
        self._atoms = atoms
        self._bonds = bonds
        self._viewer.load_molecule(atoms, bonds)
        self._atom1_spin.setMaximum(len(atoms))
        self._atom2_spin.setMaximum(len(atoms))
        self._bond_a1.setMaximum(len(atoms))
        self._bond_a2.setMaximum(len(atoms))
        self._status_bar.showMessage(f"已加载 {len(atoms)} 个原子, {len(bonds)} 个化学键（来自 fchk 文件）")

    def _on_atom_selected(self, idx):
        if idx in self._atom_selected_cache:
            self._atom_selected_cache.remove(idx)
            if self._atom1_spin.value() == idx:
                self._atom1_spin.setValue(0)
            if self._atom2_spin.value() == idx:
                self._atom2_spin.setValue(0)
        else:
            self._atom_selected_cache.append(idx)
            if len(self._atom_selected_cache) > 2:
                self._atom_selected_cache.pop(0)
            if len(self._atom_selected_cache) >= 1:
                self._atom1_spin.setValue(self._atom_selected_cache[0])
            if len(self._atom_selected_cache) >= 2:
                self._atom2_spin.setValue(self._atom_selected_cache[1])

        elem = next((a['elem'] for a in self._atoms if a['idx'] == idx), "?")
        self._atom_info_label.setText(f"原子 #{idx} ({elem})")
        self._viewer.set_highlight_atoms(self._atom_selected_cache)

    def _on_label_mode_changed(self, text):
        mode_map = {"编号": "index", "元素": "element", "元素+编号": "both", "无": "none"}
        self._viewer.set_label_mode(mode_map.get(text, "index"))

    def _on_reset_view(self):
        self._viewer.reset_view()

    def _on_start_analysis(self):
        log_file = self._log_edit.text().strip()
        if not log_file or not os.path.exists(log_file):
            QMessageBox.warning(self, "提示", "请选择有效的日志文件")
            return

        atom1 = self._atom1_spin.value()
        atom2 = self._atom2_spin.value()
        if atom1 < 1:
            QMessageBox.warning(self, "提示", "请设置原子 1")
            return
        if atom2 < 1:
            atom2 = None

        min_e2 = self._min_e2_spin.value()
        fchk_file = self._fchk_edit.text().strip() or None

        self._start_btn.setEnabled(False)
        self._status_bar.showMessage("正在运行分析...")

        self._signals = WorkerSignals()
        self._signals.analysis_done.connect(self._on_analysis_done)
        self._signals.analysis_error.connect(self._on_analysis_error)

        def worker():
            try:
                text, data = run_analysis(log_file, atom1, atom2, min_e2, fchk_file)
                self._signals.analysis_done.emit(text, data)
            except Exception as e:
                import traceback
                self._signals.analysis_error.emit(traceback.format_exc())

        threading.Thread(target=worker, daemon=True).start()

    def _on_analysis_done(self, text, data_dict):
        self._last_result = text
        self._analysis_data = data_dict
        self._result_text.setPlainText(text)
        self._start_btn.setEnabled(True)
        self._save_btn.setEnabled(True)
        self._copy_btn.setEnabled(True)
        self._status_bar.showMessage("分析完成")

        self._populate_nbo_table(data_dict)
        self._populate_e2_table(data_dict)

    def _on_analysis_error(self, err):
        self._start_btn.setEnabled(True)
        self._status_bar.showMessage("分析失败")
        QMessageBox.critical(self, "错误", f"分析出错：\n{err}")

    def _populate_nbo_table(self, data_dict):
        nbo_overview = data_dict.get("nbo_overview", [])
        self._nbo_overview_data = nbo_overview
        self._nbo_table.setRowCount(len(nbo_overview))
        for i, entry in enumerate(nbo_overview):
            self._nbo_table.setItem(i, 0, QTableWidgetItem(str(entry["nbo_id"])))
            self._nbo_table.setItem(i, 1, QTableWidgetItem(entry["type"]))
            self._nbo_table.setItem(i, 2, QTableWidgetItem(entry["atoms_str"]))
            occ = f"{entry['occupancy']:.5f}" if entry["occupancy"] is not None else "N/A"
            self._nbo_table.setItem(i, 3, QTableWidgetItem(occ))
            en = f"{entry['energy']:.6f}" if entry["energy"] is not None else "N/A"
            self._nbo_table.setItem(i, 4, QTableWidgetItem(en))
            self._nbo_table.setItem(i, 5, QTableWidgetItem(entry.get("group_label", "")))
            group = entry.get("group", "single")
            group_colors = {
                "shared": QColor("#e0effa"),
                "atom1_only": QColor("#fef3e2"),
                "atom2_only": QColor("#e8e8ff"),
            }
            if group in group_colors:
                for col in range(self._nbo_table.columnCount()):
                    item = self._nbo_table.item(i, col)
                    if item:
                        item.setBackground(group_colors[group])
        self._nbo_table.resizeColumnsToContents()

    def _populate_e2_table(self, data_dict):
        cross_e2_details = data_dict.get("cross_e2_details", [])
        self._cross_e2_details = cross_e2_details
        self._e2_table.setRowCount(len(cross_e2_details))
        for i, detail in enumerate(cross_e2_details):
            self._e2_table.setItem(i, 0, QTableWidgetItem(str(detail["idx"])))
            self._e2_table.setItem(i, 1, QTableWidgetItem(f"{detail['e2']:.2f}"))
            self._e2_table.setItem(i, 2, QTableWidgetItem(detail.get("donor_str", "")))
            self._e2_table.setItem(i, 3, QTableWidgetItem(detail.get("acceptor_str", "")))
            self._e2_table.setItem(i, 4, QTableWidgetItem(str(detail["cat"])))
            self._e2_table.setItem(i, 5, QTableWidgetItem(detail.get("stars", "")))
            self._e2_table.setItem(i, 6, QTableWidgetItem(detail.get("shared_tag", "")))
            cat = detail.get("cat", 3)
            if cat == 1:
                for col in range(self._e2_table.columnCount()):
                    item = self._e2_table.item(i, col)
                    if item:
                        item.setBackground(QColor("#d4edda"))
            elif cat == 2:
                for col in range(self._e2_table.columnCount()):
                    item = self._e2_table.item(i, col)
                    if item:
                        item.setBackground(QColor("#fff3cd"))
        self._e2_table.resizeColumnsToContents()

    def _on_nbo_table_dclick(self, row, col):
        if row >= len(self._nbo_overview_data):
            return
        entry = self._nbo_overview_data[row]
        mo_num = entry.get("mo_num")
        mo_type = entry.get("mo_type")
        if mo_num and mo_type:
            self._launch_nbo_vmd(mo_num, mo_type)

    def _on_e2_table_dclick(self, row, col):
        if row >= len(self._cross_e2_details):
            return
        detail = self._cross_e2_details[row]
        mo1 = (detail.get("mo1_num"), detail.get("mo1_type"))
        mo2 = (detail.get("mo2_num"), detail.get("mo2_type"))
        if mo1[0] and mo1[1] and mo2[0] and mo2[1]:
            self._launch_e2_vmd(mo1, mo2)
        elif mo1[0] and mo1[1]:
            self._launch_nbo_vmd(mo1[0], mo1[1])

    def _on_result_dclick(self, event):
        cursor = self._result_text.cursorForPosition(event.pos())
        cursor.select(cursor.WordUnderCursor)
        word = cursor.selectedText()
        cursor.select(cursor.BlockUnderCursor)
        line_text = cursor.selectedText()

        mo_match = re.search(r"\[(Alpha|Beta)\s+MO\s+#(\d+)\]", line_text)
        if mo_match:
            mo_type = mo_match.group(1)
            mo_num = int(mo_match.group(2))
            self._launch_nbo_vmd(mo_num, mo_type)

    def _launch_nbo_vmd(self, mo_num, mo_type):
        fchk_file = self._fchk_edit.text().strip()
        if not fchk_file or not os.path.exists(fchk_file):
            QMessageBox.warning(self, "提示", "fchk 文件路径无效")
            return

        self._start_btn.setEnabled(False)
        self._status_bar.showMessage(f"正在生成 cube：{mo_type} MO #{mo_num}...")

        signals = WorkerSignals()
        signals.vmd_ready.connect(self._on_vmd_ready_single)
        signals.vmd_error.connect(self._on_vmd_error)

        def worker():
            try:
                grid = int(self._grid_combo.currentText())
                cube = gen_cube_from_mo(fchk_file, mo_num, grid_quality=grid, multiwfn_exe=self.multiwfn_path)
                if not cube:
                    signals.vmd_error.emit(f"Failed to generate cube for {mo_type} MO #{mo_num}")
                    return
                iso = float(self._isovalue_edit.text())
                result = launch_vmd_preview(cube, isovalue=iso, vmd_exe=self.vmd_path,
                                            tachyon_exe=self.tachyon_path,
                                            style_name=self._style_combo.currentText())
                if result[0] is None:
                    signals.vmd_error.emit("Failed to launch VMD")
                    return
                self.vmd_proc, self.vmd_render_dir, _, self.vmd_port = result
                self.current_iso = iso
                signals.vmd_ready.emit(mo_num)
            except Exception as e:
                import traceback
                signals.vmd_error.emit(traceback.format_exc())

        threading.Thread(target=worker, daemon=True).start()

    def _launch_e2_vmd(self, mo1, mo2):
        fchk_file = self._fchk_edit.text().strip()
        if not fchk_file or not os.path.exists(fchk_file):
            QMessageBox.warning(self, "提示", "fchk 文件路径无效")
            return

        self._start_btn.setEnabled(False)
        mo1_num, mo1_type = mo1
        mo2_num, mo2_type = mo2
        self._status_bar.showMessage(f"正在生成双轨道 cube：{mo1_type}#{mo1_num} + {mo2_type}#{mo2_num}...")

        signals = WorkerSignals()
        signals.vmd_ready.connect(lambda _: self._on_vmd_ready_dual(mo1, mo2))
        signals.vmd_error.connect(self._on_vmd_error)

        def worker():
            try:
                grid = int(self._grid_combo.currentText())
                c1 = gen_cube_from_mo(fchk_file, mo1_num, grid_quality=grid, multiwfn_exe=self.multiwfn_path)
                if not c1:
                    signals.vmd_error.emit(f"Failed to generate cube for {mo1_type} MO #{mo1_num}")
                    return
                c2 = gen_cube_from_mo(fchk_file, mo2_num, grid_quality=grid, multiwfn_exe=self.multiwfn_path)
                if not c2:
                    signals.vmd_error.emit(f"Failed to generate cube for {mo2_type} MO #{mo2_num}")
                    return
                iso = float(self._isovalue_edit.text())
                cube_files = [(c1, f"#{mo1_num}({mo1_type})"), (c2, f"#{mo2_num}({mo2_type})")]
                result = launch_dual_vmd_preview(cube_files, isovalue=iso, vmd_exe=self.vmd_path,
                                                  style_name=self._style_combo.currentText())
                if result is None or result[0] is None:
                    signals.vmd_error.emit("Failed to launch VMD")
                    return
                self.vmd_proc, self.vmd_render_dir, self.vmd_port = result
                self.current_iso = iso
                signals.vmd_ready.emit(mo1_num)
            except Exception as e:
                import traceback
                signals.vmd_error.emit(traceback.format_exc())

        threading.Thread(target=worker, daemon=True).start()

    def _on_vmd_ready_single(self, mo_num):
        self._start_btn.setEnabled(True)
        self._render_btn.setEnabled(True)
        self._close_vmd_btn.setEnabled(True)
        self._h_filter_btn.setEnabled(True)
        self._draw_bond_btn.setEnabled(True)
        self._clear_bond_btn.setEnabled(True)
        self._iso_slider.setEnabled(True)
        self._iso_slider.setValue(int(self.current_iso * 1000))
        self._opacity_slider.setEnabled(True)
        self._status_bar.showMessage(f"VMD 已打开，预览 MO #{mo_num}")
        self._vmd_render_btn.setEnabled(True)

    def _on_vmd_ready_dual(self, mo1, mo2):
        self._start_btn.setEnabled(True)
        self._render_btn.setEnabled(True)
        self._close_vmd_btn.setEnabled(True)
        self._h_filter_btn.setEnabled(True)
        self._draw_bond_btn.setEnabled(True)
        self._clear_bond_btn.setEnabled(True)
        self._iso_slider.setEnabled(True)
        self._iso_slider.setValue(int(self.current_iso * 1000))
        self._opacity_slider.setEnabled(True)
        self._status_bar.showMessage(f"VMD 已打开，预览双轨道 {mo1[1]}#{mo1[0]} + {mo2[1]}#{mo2[0]}")
        self._vmd_render_btn.setEnabled(True)

    def _on_vmd_error(self, msg):
        self._start_btn.setEnabled(True)
        self._status_bar.showMessage("VMD 操作失败")
        QMessageBox.critical(self, "错误", msg)

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

    def _on_iso_changed(self, val):
        if not self.vmd_port:
            return
        iso = val / 1000.0
        self.current_iso = iso
        self._iso_value_label.setText(f"{iso:.3f}")
        self._isovalue_edit.setText(f"{iso:.4g}")
        for mol in range(5):
            self._send_vmd_cmd(f"mol modstyle 1 {mol} Isosurface {iso} 0 0 0 1 1")
            self._send_vmd_cmd(f"mol modstyle 2 {mol} Isosurface -{iso} 0 0 0 1 1")
        self._status_bar.showMessage(f"Isovalue = {iso:.4g}")

    def _on_opacity_changed(self, val):
        if not self.vmd_port:
            return
        op = val / 100.0
        self.current_opacity = op
        self._opacity_value_label.setText(f"{op:.2f}")
        self._send_vmd_cmd(f"material change opacity _stl_a {op}")
        self._send_vmd_cmd(f"material change opacity _stl_b {op}")
        self._status_bar.showMessage(f"Opacity = {op:.2f}")

    def _close_vmd(self):
        if self.vmd_proc and self.vmd_proc.poll() is None:
            try:
                self.vmd_proc.terminate()
                self.vmd_proc.wait(timeout=3)
            except Exception:
                try:
                    self.vmd_proc.kill()
                except Exception:
                    pass
        if self.vmd_render_dir:
            try:
                shutil.rmtree(self.vmd_render_dir, ignore_errors=True)
            except Exception:
                pass
        self.vmd_proc = None
        self.vmd_render_dir = None
        self.vmd_port = None
        self._close_persist_sock()
        self._render_btn.setEnabled(False)
        self._close_vmd_btn.setEnabled(False)
        self._h_filter_btn.setEnabled(False)
        self._h_filter_btn.setText("隐藏氢")
        self._hiding_h = False
        self._draw_bond_btn.setEnabled(False)
        self._clear_bond_btn.setEnabled(False)
        self._undo_bond_btn.setEnabled(False)
        self._iso_slider.setEnabled(False)
        self._opacity_slider.setEnabled(False)
        self._vmd_render_btn.setEnabled(False)
        self._status_bar.showMessage("VMD 已关闭")

    def _on_render(self):
        if not self.vmd_port:
            QMessageBox.warning(self, "提示", "请先打开 VMD 预览")
            return
        log_file = self._log_edit.text().strip()
        if log_file and os.path.isfile(log_file):
            out_dir = os.path.dirname(os.path.abspath(log_file))
        else:
            out_dir = os.getcwd()
        fchk_name = os.path.splitext(os.path.basename(self._fchk_edit.text()))[0] if self._fchk_edit.text() else "render"
        out_png = os.path.join(out_dir, f"{fchk_name}_render.png")

        style = self._style_combo.currentText()
        shade = self._shade_combo.currentText()
        trans = self._trans_check.isChecked()
        threads = int(self._threads_combo.currentText())
        res_str = self._res_combo.currentText()
        w, h = (int(x) for x in res_str.split("x"))

        self._render_btn.setEnabled(False)
        self._status_bar.showMessage("正在渲染...")
        self._close_persist_sock()

        def worker():
            try:
                png = render_current_view(
                    self.vmd_port, self.vmd_render_dir, output_png=out_png,
                    tachyon_exe=self.tachyon_path, resolution=(w, h),
                    style_name=style, shade_mode=shade, trans_raster=trans,
                    threads=threads
                )
                if png:
                    sig.append_text.emit(f"渲染完成: {os.path.basename(png)}")
                    try:
                        os.startfile(png)
                    except Exception:
                        pass
                else:
                    sig.append_text.emit("渲染失败，请检查 Tachyon 是否正常")
            except Exception as e:
                sig.append_text.emit(f"渲染错误: {e}")
            finally:
                self._render_btn.setEnabled(True)

        sig = WorkerSignals()
        sig.append_text.connect(lambda t: self._status_bar.showMessage(t))

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def _on_save(self):
        if not self._last_result:
            QMessageBox.warning(self, "提示", "请先运行分析")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Results", "", "Text files (*.txt);;All files (*.*)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._last_result)
            self._status_bar.showMessage(f"已保存至 {os.path.basename(path)}")
            QMessageBox.information(self, "已保存", f"结果已保存至：\n{path}")

    def _on_copy(self):
        if not self._last_result:
            return
        QApplication.clipboard().setText(self._last_result)
        self._status_bar.showMessage("结果已复制到剪贴板")

    def _toggle_h_filter(self):
        if not self.vmd_port:
            QMessageBox.warning(self, "提示", "请先打开 VMD 预览")
            return
        self._hiding_h = not getattr(self, '_hiding_h', False)
        if self._hiding_h:
            self._h_filter_btn.setText("显示氢")
            h_str = self._h_indices_edit.text().strip()
            if h_str:
                try:
                    keep = [int(x.strip()) for x in h_str.split(",") if x.strip()]
                    idx_str = " ".join(map(str, keep))
                    sel = f"not element H or (element H and index {idx_str})"
                except ValueError:
                    sel = "not element H"
            else:
                sel = "not element H"
            cmd = f'foreach mid [molinfo list] {{ mol modselect 0 $mid "{sel}" }}'
            self._send_vmd_cmd(cmd)
            self._status_bar.showMessage("氢原子已隐藏")
        else:
            self._h_filter_btn.setText("隐藏氢")
            self._send_vmd_cmd('foreach mid [molinfo list] { mol modselect 0 $mid all }')
            self._status_bar.showMessage("已恢复显示全部原子")

    def _draw_bond(self):
        if not self.vmd_port:
            QMessageBox.warning(self, "提示", "请先打开 VMD 预览")
            return
        a1 = self._bond_a1.value()
        a2 = self._bond_a2.value()
        color = self._bond_color.currentText()
        btype = self._bond_type.currentText()
        cmd = (f"draw_bond -mol1 top -index1 {a1} -mol2 top -index2 {a2} "
               f"-color {color} -h_type {btype} -h_radius 0.08 -mat HalfTransparent")
        resp = self._send_vmd_cmd(cmd)
        if resp and "ERROR" not in resp:
            self._status_bar.showMessage(f"已绘制键 {a1}-{a2} ({color} {btype})")
            self._undo_bond_btn.setEnabled(True)
        else:
            self._status_bar.showMessage("键绘制失败")

    def _undo_bond(self):
        if self._send_vmd_cmd("draw_bond_undo"):
            self._status_bar.showMessage("已撤销上次绘制")

    def _clear_bond(self):
        if self._send_vmd_cmd("draw_bond_clear"):
            self._status_bar.showMessage("已清除所有虚线键")
            self._undo_bond_btn.setEnabled(False)

    def _open_settings(self):
        self._save_tool_paths()

    def _save_paths_now(self):
        self._save_tool_paths()

    def closeEvent(self, event):
        self._close_vmd()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 9))

    palette = app.palette()
    palette.setColor(QPalette.AlternateBase, QColor("#edf2f9"))
    app.setPalette(palette)

    window = MainWindow()
    window._atom_selected_cache = []
    window._hiding_h = False
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
