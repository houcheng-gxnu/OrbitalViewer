#!/usr/bin/env python3
"""
Gaussian log 分子结构渲染工具 v1.1
Multiwfn (log -> xyz) + VMD (预览 + Tachyon 渲染) + Tachyon (scene -> BMP/PNG)

特性：
  - 集成 vcube2.0 (钟诚) 的 11 种渲染样式
  - VMD GUI 预览 -> 手动调整视角 -> 一键 Tachyon 渲染
  - 支持批量自动渲染和手动预览两种模式
  - 支持球棍/线框/CPK/VDW 多种分子表示方式
  - 渲染输出文件名与 log 一致

用法：
  直接运行 -> 弹出 GUI
  命令行 -> python log_render.py folder/ --style sob-art
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
    "log_render.ini"
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
STYLES = {
    "sob_Gold": {
        "tachyon_options": "-trans_raster3d",
        "lights": {"0": "on", "1": "on", "2": "off", "3": "on"},
        "shadows": "off", "ao": "off",
        "aoambient": "0.8", "aodirect": "0.3",
        "surface_mat": [0.1, 0.6, 1.0, 1.0, 0.0, 0.75, 0.0, 0.0],
        "surface_mat_b": [0.1, 0.6, 1.0, 1.0, 0.0, 0.75, 0.0, 0.0],
        "pos_color": [12, None, None],
        "neg_color": [22, None, None],
        "atom_cpk": "0.600000 0.400000 30.000000 30.000000",
        "atom_mat": [0.0, 0.65, 0.5, 0.53, 0.15, 1.0, 2.0, 0.3],
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
    "Sob_Silver": {
        "tachyon_options": "-trans_raster3d",
        "lights": {"0": "on", "1": "on", "2": "on", "3": "off"},
        "shadows": "on", "ao": "on",
        "surface_mat": [0.20, 0.8, 0.7, 0.3, 0.0, 0.7, 0.0, 0.0],
        "surface_mat_b": [0.20, 0.8, 0.7, 0.3, 0.0, 0.7, 0.0, 0.0],
        "pos_color": [31, 0.900, 0.500, 0.200],
        "neg_color": [32, 0.000, 0.600, 0.800],
        "atom_cpk": "0.700000 0.350000 30.000000 30.000000",
        "atom_mat": [0.0, 0.85, 0.0, 0.53, 0.0, 1.0, 0.5, 0.9],
        "c_color": "gray", "c_rgb": "0.5569 0.5569 0.5569",
    },
}


# 原子元素着色（所有样式共用，来自 vcube2.0）
ATOM_COLORS = """
color change rgb 101 0.8000 0.8000 0.8000
color change rgb 102 0.8471 1.0000 1.0000
color change rgb 103 0.8000 0.4863 1.0000
color change rgb 104 0.8000 1.0000 0.0000
color change rgb 105 1.0000 0.7098 0.7098
color change rgb 106 0.7000 0.5600 0.3600
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
"""

# 分子表示方式
REPRESENTATIONS = {
    "CPK": "CPK {cpk_params}",
    "Licorice": "Licorice 0.2 12 12",
    "VDW": "VDW 1.0 12",
    "Bonds": "Bonds 0.3 12",
    "Lines": "Lines 1.0",
}

CPK_PRESETS = {
    "default": "0.600000 0.400000 30.000000 30.000000",
    "large": "0.800000 0.400000 30.000000 30.000000",
    "small": "0.400000 0.300000 30.000000 30.000000",
}


# ── Multiwfn：log -> xyz ─────────────────────────────────
def log_to_xyz(log_path, multiwfn_exe=None, work_dir=None):
    """
    调用 Multiwfn 从 Gaussian log 文件提取优化后几何构型，导出为 xyz 文件。
    Multiwfn 交互：打开 log → 100(可视化和绘图) → 2(查看当前体系结构) → 2(标准xyz) → 文件名 → 0 → q
    返回 xyz 文件路径，失败返回 None。
    """
    if multiwfn_exe is None:
        multiwfn_exe = DEFAULT_MULTIWFN
    if work_dir is None:
        work_dir = os.path.dirname(os.path.abspath(log_path))
    os.makedirs(work_dir, exist_ok=True)

    log_name = os.path.basename(log_path)
    ascii_dir = os.path.join(work_dir, "_multiwfn_tmp")
    os.makedirs(ascii_dir, exist_ok=True)
    ascii_log = os.path.join(ascii_dir, log_name)
    if not os.path.exists(ascii_log):
        shutil.copy2(log_path, ascii_log)

    # Multiwfn 交互：打开 log -> 100(可视化和绘图) -> 2(查看当前体系结构) -> 2(标准xyz) -> 回车 -> 0(返回) -> q
    xyz_name = "temp.xyz"
    inputs = (
        "\n" + log_name + "\n100\n2\n2\n" + xyz_name + "\n0\nq\n"
    )

    try:
        subprocess.run(
            multiwfn_exe, input=inputs, capture_output=True,
            cwd=ascii_dir, timeout=600, encoding="utf-8", errors="replace",
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"  错误: {e}")
        return None

    xyz_src = os.path.join(ascii_dir, xyz_name)
    if not os.path.exists(xyz_src):
        try:
            shutil.rmtree(ascii_dir)
        except OSError:
            pass
        return None

    stem = os.path.splitext(log_name)[0]
    xyz_dst = os.path.join(work_dir, f"{stem}.xyz")
    shutil.move(xyz_src, xyz_dst)
    try:
        shutil.rmtree(ascii_dir)
    except OSError:
        pass
    return xyz_dst


def _style_tcl_mol(mol_name, style_name, representation="CPK", cpk_scale="1.0", shade_mode="full", keep_h_indices=None):
    """
    根据 xyz 文件名和样式名生成 VMD TCL 脚本（分子结构渲染，不含 socket 服务器和 render 命令）。
    VMD 读取 xyz 格式分子结构。
    shade_mode: 'full'=全阴影, 'medium'=中等阴影, 'noshadow'=无阴影
    keep_h_indices: 要保留的氢原子序号列表（从0开始），None表示保留所有氢原子
    """
    s = STYLES.get(style_name, STYLES["sob_Gold"])

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

    # 原子材质
    mat_names = ["ambient", "diffuse", "specular", "shininess", "mirror", "opacity", "outline", "outlinewidth"]
    atom_mat_lines = "if {[lsearch [material list] _stl_atom] < 0} {material add _stl_atom}\n"
    for name, val in zip(mat_names, s["atom_mat"]):
        atom_mat_lines += f"material change {name} _stl_atom {val}\n"

    # 球棍材质（用于 Licorice）
    bond_mat_lines = "if {[lsearch [material list] _stl_bond] < 0} {material add _stl_bond}\n"
    bond_mat_vals = [0.1, 0.7, 0.4, 0.5, 0.0, 1.0, 0.0, 0.0]
    for name, val in zip(mat_names, bond_mat_vals):
        bond_mat_lines += f"material change {name} _stl_bond {val}\n"

    # 分子表示：CPK 用样式的 atom_cpk（球半径比, 键半径比），与 fchk_orbital 一致
    atom_cpk = s.get("atom_cpk", "0.600000 0.400000 30.000000 30.000000")
    
    # 应用 cpk_scale 缩放因子
    cpk_parts = atom_cpk.split()
    if len(cpk_parts) >= 2:
        try:
            # 缩放第一个和第二个值（球半径比和键半径比）
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
        rep_style = f"CPK {atom_cpk}"
        rep_material = "_stl_atom"
    elif representation == "Licorice":
        rep_style = "Licorice 0.2 12 12"
        rep_material = "_stl_bond"
    elif representation == "VDW":
        # VDM 只用球半径比（atom_cpk 第一个值）
        vdw_scale = atom_cpk.split()[0]
        rep_style = f"VDW {vdw_scale} 12"
        rep_material = "_stl_atom"
    elif representation == "Bonds":
        rep_style = "Bonds 0.3 12"
        rep_material = "_stl_bond"
    else:  # Lines
        rep_style = "Lines 1.0"
        rep_material = "_stl_atom"

    # 处理氢原子过滤 —— 在加载分子并设置样式之后再执行过滤
    # 使用纯选择字符串拼接，不依赖不存在的 $sel union 方法
    if keep_h_indices is not None:
        if keep_h_indices:
            # 保留指定氢原子：选择"非氢 OR 指定氢"
            h_idx_list = " ".join(map(str, keep_h_indices))
            h_sel_str = f"not element H or (element H and index {h_idx_list})"
        else:
            # 删除所有氢原子
            h_sel_str = "not element H"
        h_filter_code = f"""
# 隐藏氢原子（在样式设置完成后执行）
set _h_sel [atomselect top "{h_sel_str}"]
if {{[$_h_sel num] > 0}} {{
    $_h_sel writepdb _temp_hfilter.pdb
    mol delete top
    mol new _temp_hfilter.pdb type pdb waitfor all
    file delete _temp_hfilter.pdb
    mol modstyle 0 top {rep_style}
    mol modmaterial 0 top {rep_material}
    mol modcolor 0 top Element
    color Element C {s['c_color']}
    color change rgb {s['c_color']} {s['c_rgb']}
}}
$_h_sel delete
"""
    else:
        h_filter_code = ""

    # 额外材质设置
    extra_mat_lines = s.get("extra_mat_lines", [])
    extra_mat_tcl = "\n".join(extra_mat_lines) + "\n" if extra_mat_lines else ""
    
    # 显示距离
    display_dist = s.get("display_distance", "-8.0")
    
    return f"""color Display Background white
axes location Off
display depthcue off
display projection Orthographic
display rendermode GLSL

{light_lines}
{shadow_lines}

# 加载 xyz 文件
mol new {mol_name} type xyz first 0 last 0 step 1 waitfor all

# 分子表示
mol modstyle 0 top {rep_style}
mol modmaterial 0 top {rep_material}
mol modcolor 0 top Element
{atom_mat_lines}
{bond_mat_lines}
{ATOM_COLORS}
color Element C {s['c_color']}
color change rgb {s['c_color']} {s['c_rgb']}

{extra_mat_tcl}
display distance {display_dist}
display height 10

{h_filter_code}
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
    set dist [veclength [vecsub $pos2 $pos1]]
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


# ── VMD 预览：打开 GUI 窗口 + socket 服务器 ──────────────
def preview_mol(xyz_path, style_name="sob_Gold", representation="CPK",
                cpk_scale="1.0", vmd_exe=None, shade_mode="full", keep_h_indices=None):
    """
    打开 VMD GUI 窗口预览 xyz 文件，并启动 socket 服务器等待渲染命令。
    返回: (port, render_dir) 或 (None, None)
    """
    if vmd_exe is None:
        vmd_exe = DEFAULT_VMD
    mol_name = os.path.basename(xyz_path)
    work_dir = os.path.dirname(os.path.abspath(xyz_path))

    # 检测中文路径
    try:
        xyz_path.encode("ascii")
        has_nonascii = False
    except UnicodeEncodeError:
        has_nonascii = True

    if has_nonascii:
        render_dir = tempfile.mkdtemp(prefix="vmd_")
        tmp_mol = os.path.join(render_dir, mol_name)
        shutil.copy2(xyz_path, tmp_mol)
    else:
        render_dir = work_dir

    # 找空闲端口
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    # 样式 TCL + socket 服务器
    style_tcl = _style_tcl_mol(mol_name, style_name, representation, cpk_scale, shade_mode=shade_mode, keep_h_indices=keep_h_indices)
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
    if {{$cmd eq ""}} return

    if [catch {{uplevel #0 $cmd}} err] {{
        puts $chan "ERROR: $err"
    }} else {{
        puts $chan "OK"
    }}
    flush $chan
}}

puts "==========================================="
puts " VMD 分子预览已就绪 (样式: {style_name})"
puts " 在 Python GUI 中点击 [渲染当前视角] 按钮"
puts " 端口: {port}"
puts "==========================================="

# === 原子拾取处理 ===
proc _vmd_pick_atom {{args}} {{
    set idx $::vmd_pick_atom
    if {{$idx != ""}} {{
        set sel [atomselect top "index $idx"]
        if {{[$sel num] > 0}} {{
            set atomtype [$sel get type]
            puts "ATOM_PICK: index=$idx type=$atomtype"
            set fd [open "pick_result.txt" w]
            puts $fd "ATOM_PICK: index=$idx type=$atomtype"
            close $fd
        }}
        $sel delete
    }}
}}
trace variable vmd_pick_atom w _vmd_pick_atom
"""
    tcl = style_tcl + _draw_bond_tcl() + socket_tcl
    tcl_path = os.path.join(render_dir, "_preview.tcl")
    with open(tcl_path, "w") as f:
        f.write(tcl)

    subprocess.Popen(
        [vmd_exe, "-e", "_preview.tcl"],
        cwd=render_dir,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )

    return port, render_dir


# ── 通过 socket 发送渲染命令到 VMD ─────────────────────
def render_current_view(port, render_dir, output_png=None,
                        tachyon_exe=None, resolution=(2000, 1500),
                        style_name="sob_Gold", shade_mode="full"):
    """
    连接到 VMD 的 socket 服务器，发送 render Tachyon 命令，
    然后用 Tachyon 渲染成 PNG。
    """
    if tachyon_exe is None:
        tachyon_exe = DEFAULT_TACHYON
    s = STYLES.get(style_name, STYLES["sob_Gold"])

    # 连接 VMD socket
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

    # 清理旧文件
    for fn in ["vmdscene.dat", "_render.bmp"]:
        fp = os.path.join(render_dir, fn)
        if os.path.exists(fp):
            os.remove(fp)

    resp = send_cmd("render Tachyon vmdscene.dat")
    vmd_sock.close()

    dat = os.path.join(render_dir, "vmdscene.dat")
    if not os.path.exists(dat):
        return None

    # Tachyon 渲染
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
        output_png = os.path.join(render_dir, "render.png")

    try:
        from PIL import Image
        img = Image.open(bmp)
        img.save(output_png)
    except ImportError:
        output_png = bmp

    return output_png


# ── 自动渲染（无预览，批量模式用）─────────────────────────
def render_mol_auto(xyz_path, output_png=None,
                    style_name="sob_Gold", representation="CPK",
                    cpk_scale="1.0", resolution=(2000, 1500),
                    vmd_exe=None, tachyon_exe=None, shade_mode="full", keep_h_indices=None):
    """自动渲染（不打开 VMD GUI），用于批量模式。"""
    if vmd_exe is None:
        vmd_exe = DEFAULT_VMD
    if tachyon_exe is None:
        tachyon_exe = DEFAULT_TACHYON
    if output_png is None:
        output_png = os.path.splitext(xyz_path)[0] + ".png"

    mol_name = os.path.basename(xyz_path)
    work_dir = os.path.dirname(os.path.abspath(xyz_path))

    try:
        xyz_path.encode("ascii")
        has_nonascii = False
    except UnicodeEncodeError:
        has_nonascii = True

    if has_nonascii:
        tmp_dir = tempfile.mkdtemp(prefix="vmd_")
        tmp_mol = os.path.join(tmp_dir, mol_name)
        shutil.copy2(xyz_path, tmp_mol)
        render_dir = tmp_dir
    else:
        render_dir = work_dir

    s = STYLES.get(style_name, STYLES["sob_Gold"])
    style_tcl = _style_tcl_mol(mol_name, style_name, representation, cpk_scale, shade_mode=shade_mode, keep_h_indices=keep_h_indices)
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
            dst = os.path.splitext(xyz_path)[0] + ".bmp"
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
            self.root.title("分子结构渲染 v1.2 — VMD/Tachyon (Gaussian log)")
            self.root.geometry("780x820")
            self.running = False

            self.vmd_port = None
            self.vmd_render_dir = None
            self.vmd_process = None
            self.vmd_log_path = None
            self.vmd_xyz_path = None

            self.bond_colors = {
                "黑色": "black", "灰色": "gray", "青色": "cyan", "黄色": "yellow",
                "红色": "red", "蓝色": "blue", "绿色": "green",
                "白色": "white", "橙色": "orange", "紫色": "purple",
            }
            self.bond_types = {
                "虚线(pymol)": "pymol", "圆点(dots)": "dots",
                "实线圆柱": "cylinder", "球体": "sphere",
                "圆锥": "cone", "线条": "line",
            }
            self.bond_mats = {
                "不透明": "Opaque", "50%透明": "HalfTransparent",
                "透明": "Transparent",
            }

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
            frm1 = ttk.LabelFrame(root, text="输入 (.log 文件)")
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

            # 样式
            r_style = ttk.Frame(frm2); r_style.pack(fill="x", padx=5, pady=2)
            ttk.Label(r_style, text="样式:").pack(side="left")
            style_names = list(STYLES.keys())
            style_display = [f"{n}" for n in style_names]
            self.var_style = tk.StringVar(value=style_display[0])
            self.style_combo = ttk.Combobox(r_style, textvariable=self.var_style,
                                            width=40, values=style_display, state="readonly")
            self.style_combo.pack(side="left", padx=5)
            self.style_combo.current(0)
            # 样式选择实时更新 VMD 显示
            self.var_style.trace_add('write', self._on_style_change)

            # 表示方式 + 缩放
            r_rep = ttk.Frame(frm2); r_rep.pack(fill="x", padx=5, pady=2)
            ttk.Label(r_rep, text="表示:").pack(side="left")
            self.var_rep = tk.StringVar(value="CPK")
            rep_combo = ttk.Combobox(r_rep, textvariable=self.var_rep, width=10,
                                     values=list(REPRESENTATIONS.keys()), state="readonly")
            rep_combo.pack(side="left", padx=5)
            ttk.Label(r_rep, text="  缩放:").pack(side="left")
            self.var_scale = tk.StringVar(value="1.0")
            ttk.Entry(r_rep, textvariable=self.var_scale, width=5).pack(side="left", padx=5)
            ttk.Label(r_rep, text="(CPK/VDW半径比)").pack(side="left")

            # 分辨率
            r_res = ttk.Frame(frm2); r_res.pack(fill="x", padx=5, pady=2)
            ttk.Label(r_res, text="分辨率:").pack(side="left")
            self.var_res = tk.StringVar(value="2000x1500")
            ttk.Combobox(r_res, textvariable=self.var_res, width=12,
                         values=["2000x1500", "1200x900", "3000x2250"],
                         state="readonly"
                         ).pack(side="left", padx=5)
            self.var_shade = tk.StringVar(value="full")
            ttk.Label(r_res, text="光影:").pack(side="left", padx=(20, 0))
            for text, val in [("Full", "full"), ("Medium", "medium")]:
                ttk.Radiobutton(r_res, text=text, variable=self.var_shade,
                                value=val).pack(side="left", padx=3)

            # 模式
            r3 = ttk.Frame(frm2); r3.pack(fill="x", padx=5, pady=2)
            self.var_auto = tk.BooleanVar(value=False)
            ttk.Checkbutton(r3, text="自动渲染（不预览，批量模式）",
                            variable=self.var_auto).pack(side="left")
            self.var_open = tk.BooleanVar(value=False)
            ttk.Checkbutton(r3, text="完成后打开文件夹",
                            variable=self.var_open).pack(side="left", padx=20)

            # 氢原子过滤
            r_h = ttk.Frame(frm2); r_h.pack(fill="x", padx=5, pady=2)
            ttk.Label(r_h, text="氢原子:").pack(side="left")
            self.var_h_filter = tk.BooleanVar(value=False)
            self.btn_h_filter = ttk.Button(r_h, text="隐藏所有氢原子", 
                                          command=self._toggle_h_filter,
                                          style="Toggle.TButton")
            self.btn_h_filter.pack(side="left")
            ttk.Label(r_h, text="保留序号:").pack(side="left", padx=(10, 0))
            self.var_h_indices = tk.StringVar(value="")
            ttk.Entry(r_h, textvariable=self.var_h_indices, width=20).pack(side="left", padx=2)
            ttk.Label(r_h, text="(逗号分隔，从0开始，如: 0,5,8)").pack(side="left")

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
            self.btn_run = ttk.Button(frm4, text="  VMD预览  ", command=self._run)
            self.btn_run.pack(side="left", padx=5)
            self.btn_render = ttk.Button(frm4, text="  渲染当前视角  ", command=self._render_view,
                                         state="disabled")
            self.btn_render.pack(side="left", padx=5)
            self.btn_stop = ttk.Button(frm4, text="  停止  ", command=self._stop,
                                       state="disabled")
            self.btn_stop.pack(side="left", padx=5)

            # ── 画虚线 ──
            frm_bond = ttk.LabelFrame(root, text="画虚线 (预览后可用)")
            frm_bond.pack(fill="x", padx=10, pady=5)

            rb1 = ttk.Frame(frm_bond); rb1.pack(fill="x", padx=5, pady=2)
            ttk.Label(rb1, text="原子1:").pack(side="left")
            self.var_ba1 = tk.StringVar(value="0")
            ttk.Entry(rb1, textvariable=self.var_ba1, width=6).pack(side="left", padx=2)
            ttk.Label(rb1, text="原子2:").pack(side="left", padx=(8, 0))
            self.var_ba2 = tk.StringVar(value="1")
            ttk.Entry(rb1, textvariable=self.var_ba2, width=6).pack(side="left", padx=2)

            ttk.Label(rb1, text="颜色:").pack(side="left", padx=(8, 0))
            self.var_bcolor = tk.StringVar(value="灰色")
            ttk.Combobox(rb1, textvariable=self.var_bcolor, width=6,
                         values=list(self.bond_colors.keys()),
                         state="readonly").pack(side="left", padx=2)

            ttk.Label(rb1, text="类型:").pack(side="left", padx=(8, 0))
            self.var_btype = tk.StringVar(value="圆点(dots)")
            ttk.Combobox(rb1, textvariable=self.var_btype, width=10,
                         values=list(self.bond_types.keys()),
                         state="readonly").pack(side="left", padx=2)

            ttk.Label(rb1, text="材质:").pack(side="left", padx=(8, 0))
            self.var_bmat = tk.StringVar(value="50%透明")
            ttk.Combobox(rb1, textvariable=self.var_bmat, width=8,
                         values=list(self.bond_mats.keys()),
                         state="readonly").pack(side="left", padx=2)

            rb2 = ttk.Frame(frm_bond); rb2.pack(fill="x", padx=5, pady=2)
            ttk.Label(rb2, text="段数:").pack(side="left")
            self.var_bnbars = tk.StringVar(value="10")
            ttk.Entry(rb2, textvariable=self.var_bnbars, width=5).pack(side="left", padx=2)
            ttk.Label(rb2, text="间距:").pack(side="left", padx=(6, 0))
            self.var_bspace = tk.StringVar(value="1.2")
            ttk.Entry(rb2, textvariable=self.var_bspace, width=5).pack(side="left", padx=2)
            ttk.Label(rb2, text="半径:").pack(side="left", padx=(6, 0))
            self.var_bradius = tk.StringVar(value="0.06")
            ttk.Entry(rb2, textvariable=self.var_bradius, width=5).pack(side="left", padx=2)

            self.btn_draw_bond = ttk.Button(rb2, text="  画虚线  ",
                                            command=self._draw_bond, state="disabled")
            self.btn_draw_bond.pack(side="left", padx=(12, 2))
            self.btn_undo_bond = ttk.Button(rb2, text="撤销",
                                            command=self._undo_bond, state="disabled")
            self.btn_undo_bond.pack(side="left", padx=2)
            ttk.Button(rb2, text="清除全部",
                       command=self._clear_bonds).pack(side="left", padx=2)

            # ── 进度 ──
            self.var_prog = tk.StringVar(value="就绪")
            ttk.Label(root, textvariable=self.var_prog).pack(fill="x", padx=10)

            # ── 日志 ──
            self.log = tk.Text(root, height=6, font=("Consolas", 9),
                               bg="#1e1e1e", fg="#d4d4d4", insertbackground="white")
            self.log.pack(fill="both", expand=True, padx=10, pady=5)

        def _get_style_name(self):
            val = self.var_style.get().strip()
            if val:
                return val.split("  ")[0].strip()
            return "sob_Gold"

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
                p = filedialog.askdirectory(title="选择含 .log 的文件夹")
            else:
                p = filedialog.askopenfilename(
                    title="选择 Gaussian log",
                    filetypes=[("Gaussian Log", "*.log")])
            if p:
                self.var_path.set(p)

        def _browse_out(self):
            p = filedialog.askdirectory(title="选择输出目录")
            if p:
                self.var_out.set(p)

        def _send_to_vmd(self, cmd):
            """通过 socket 向 VMD 发送命令"""
            if hasattr(self, 'vmd_port') and self.vmd_port:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.connect(("127.0.0.1", self.vmd_port))
                    sock.sendall((cmd + "\n").encode())
                    # 等待一小段时间让 VMD 处理命令，然后优雅关闭
                    import time
                    time.sleep(0.05)
                    sock.shutdown(socket.SHUT_WR)
                    sock.close()
                    return True
                except Exception as e:
                    self._append(f"发送命令失败: {e}")
                    return False
            return False

        def _poll_pick_file(self):
            """轮询检查pick_result.txt文件，捕获VMD中拾取的原子信息"""
            if not hasattr(self, 'vmd_render_dir') or not self.vmd_render_dir:
                return
            pick_file = os.path.join(self.vmd_render_dir, "pick_result.txt")
            if os.path.exists(pick_file):
                try:
                    with open(pick_file, 'r') as f:
                        content = f.read().strip()
                    os.remove(pick_file)
                    self._append(f"[调试] 读取到文件内容: {content}")
                    if content.startswith("ATOM_PICK:"):
                        parts = content.split()
                        atom_index = ""
                        atom_type = ""
                        for p in parts:
                            if p.startswith("index="):
                                atom_index = p.split("=")[1]
                            elif p.startswith("type="):
                                atom_type = p.split("=")[1]
                        if atom_index and atom_type:
                            self._append(f"[原子拾取] 类型: {atom_type}, 编号: {atom_index}")
                except Exception as e:
                    self._append(f"读取拾取信息失败: {e}")
            if hasattr(self, 'vmd_port') and self.vmd_port:
                self.root.after(300, self._poll_pick_file)

        def _on_style_change(self, *args):
            """样式改变时实时更新 VMD 显示"""
            if not hasattr(self, 'vmd_port') or not self.vmd_port:
                return
            
            # 获取新选择的样式
            style_display = self.var_style.get().strip()
            style_name = style_display.split()[0]
            
            if style_name in STYLES:
                self._apply_style_to_vmd(style_name)
                self._append(f"已切换样式: {style_display}")

        def _apply_style_to_vmd(self, style_name):
            """将指定样式应用到 VMD"""
            s = STYLES.get(style_name, STYLES["sob_Gold"])
            
            # 使用存储的样式参数，保持一致性
            rep_style = getattr(self, '_current_rep_style', 'CPK 0.600000 0.400000 30.000000 30.000000')
            rep_material = getattr(self, '_current_rep_material', '_stl_atom')
            
            # 更新样式名称
            self.vmd_style_name = style_name
            
            # 发送命令到 VMD
            self._send_to_vmd(f"mol modstyle 0 top {rep_style}")
            self._send_to_vmd(f"mol modmaterial 0 top {rep_material}")
            
            # 设置颜色和光照
            self._send_to_vmd(f"mol modcolor 0 top Element")
            self._send_to_vmd(f"color Element C {s.get('c_color', 'tan')}")
            
            # 设置材质属性
            self._send_to_vmd(f"material diffuse {rep_material} {s.get('diffuse', '0.8')}")
            self._send_to_vmd(f"material specular {rep_material} {s.get('specular', '0.2')}")
            self._send_to_vmd(f"material shininess {rep_material} {s.get('shininess', '10')}")
            self._send_to_vmd(f"material ambient {rep_material} {s.get('ambient', '0.2')}")
            self._send_to_vmd(f"material opacity {rep_material} {s.get('opacity', '1.0')}")

        def _toggle_h_filter(self):
            # 检查 VMD 是否已启动
            if not hasattr(self, 'vmd_port') or not self.vmd_port:
                self._append("请先点击预览按钮启动 VMD")
                return

            self.var_h_filter.set(not self.var_h_filter.get())
            if self.var_h_filter.get():
                self.btn_h_filter.config(text="显示所有氢原子")
                # 构建选择字符串：不含氢 or 保留指定氢
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
                # 确定当前样式参数，用于重新应用
                rep_style = getattr(self, '_current_rep_style', 'CPK 0.600000 0.400000 30.000000 30.000000')
                rep_material = getattr(self, '_current_rep_material', '_stl_atom')
                cmd = (
                    f'set _h_sel [atomselect top "{sel_str}"];'
                    f' if {{[$_h_sel num] > 0}} {{'
                    f'   $_h_sel writepdb _temp_hfilter.pdb;'
                    f'   mol delete top;'
                    f'   mol new _temp_hfilter.pdb type pdb waitfor all;'
                    f'   file delete _temp_hfilter.pdb;'
                    f'   mol modstyle 0 top {rep_style};'
                    f'   mol modmaterial 0 top {rep_material};'
                    f'   mol modcolor 0 top Element'
                    f' }};'
                    f' $_h_sel delete'
                )
                self._send_to_vmd(cmd)
            else:
                self.btn_h_filter.config(text="隐藏所有氢原子")
                # 重新加载原始分子并应用样式
                if hasattr(self, 'vmd_xyz_path') and self.vmd_xyz_path:
                    xyz_name = os.path.basename(self.vmd_xyz_path)
                    if hasattr(self, 'vmd_render_dir') and self.vmd_render_dir:
                        xyz_path = os.path.join(self.vmd_render_dir, xyz_name)
                    else:
                        xyz_path = os.path.abspath(self.vmd_xyz_path)

                    # 使用存储的当前样式参数，保持一致性
                    rep_style = getattr(self, '_current_rep_style', 'CPK 0.600000 0.400000 30.000000 30.000000')
                    rep_material = getattr(self, '_current_rep_material', '_stl_atom')

                    self._send_to_vmd(f"mol delete top")
                    self._send_to_vmd(f"mol new {{{xyz_path}}} type xyz first 0 last 0 step 1 waitfor all")
                    self._send_to_vmd(f"mol modstyle 0 top {rep_style}")
                    self._send_to_vmd(f"mol modmaterial 0 top {rep_material}")
                    self._send_to_vmd(f"mol modcolor 0 top Element")
                    self._send_to_vmd(f"color Element C {s['c_color']}")
                    self._send_to_vmd(f"color change rgb {s['c_color']} {s['c_rgb']}")
                    self._send_to_vmd("display distance -8.0")
                    self._send_to_vmd("display height 10")

        def _append(self, msg):
            self.log.insert("end", msg + "\n")
            self.log.see("end")
            self.root.update_idletasks()

        def _get_params(self):
            style_name = self._get_style_name()
            representation = self.var_rep.get().strip()
            try:
                cpk_scale = self.var_scale.get()
            except ValueError:
                cpk_scale = 0.6
            try:
                res_str = self.var_res.get().strip()
                w, h = res_str.split("x")
                resolution = (int(w), int(h))
            except (ValueError, AttributeError):
                resolution = (2000, 1500)
            
            # 解析氢原子过滤参数
            keep_h_indices = None
            if self.var_h_filter.get():
                h_str = self.var_h_indices.get().strip()
                if h_str:
                    try:
                        keep_h_indices = [int(x.strip()) for x in h_str.split(",") if x.strip()]
                    except ValueError:
                        keep_h_indices = None
                else:
                    # 空字符串表示删除所有氢原子
                    keep_h_indices = []
            
            return style_name, representation, cpk_scale, resolution, self.var_shade.get(), keep_h_indices

        def _run(self):
            """批量渲染所有 log 文件"""
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

            files = (sorted(glob.glob(os.path.join(path, "*.log")))
                     if os.path.isdir(path) else [path])
            if not files:
                messagebox.showwarning("提示", "未找到 .log 文件")
                return

            out = self.var_out.get().strip() or (
                path if os.path.isdir(path) else os.path.dirname(path))
            os.makedirs(out, exist_ok=True)

            style_name, representation, cpk_scale, resolution, shade_mode, keep_h_indices = self._get_params()
            auto = self.var_auto.get()
            do_open = self.var_open.get()


            self.running = True
            self.btn_run.config(state="disabled")
            self.btn_render.config(state="disabled")
            self.btn_stop.config(state="normal")

            def worker():
                total = len(files)
                self._append(f"{total} 个文件 -> {out}")
                self._append(f"样式={style_name}  表示={representation}  缩放={cpk_scale}  res={resolution[0]}x{resolution[1]}")
                self._append("流程: log -> Multiwfn(xyz) -> VMD/Tachyon(PNG)")
                if auto:
                    self._append("模式: 自动渲染（无预览）")
                else:
                    self._append("模式: 预览 -> 手动调整 -> 渲染")
                self._append("=" * 50)
                ok = 0
                xyz_files = []
                t_total = time.time()

                # 第一步：所有 log -> xyz
                self._append("\n[步骤1] Multiwfn: log -> xyz")
                for i, log_file in enumerate(files):
                    if not self.running:
                        self._append("已停止"); break
                    name = os.path.basename(log_file)
                    self.var_prog.set(f"[转换 {i+1}/{total}] {name}")
                    self._append(f"\n[转换 {i+1}/{total}] {name}")

                    t0 = time.time()
                    xyz = log_to_xyz(log_file,
                                     multiwfn_exe=exe_paths["multiwfn"],
                                     work_dir=out)
                    dt = time.time() - t0
                    if not xyz:
                        self._append(f"  xyz 转换失败 ({dt:.1f}s)")
                        continue
                    self._append(f"  xyz OK ({dt:.1f}s) -> {os.path.basename(xyz)}")
                    xyz_files.append(xyz)

                # 第二步：渲染
                if not self.running:
                    pass
                elif not auto and xyz_files:
                    # 非自动模式：预览第一个 xyz
                    xyz_file = xyz_files[0]
                    name = os.path.basename(xyz_file)
                    self.var_prog.set(f"[预览] {name}")
                    self._append(f"\n[步骤2] VMD 预览: {name}")
                    try:
                        port, render_dir = preview_mol(
                            xyz_file, style_name=style_name,
                            representation=representation, cpk_scale=str(cpk_scale),
                            vmd_exe=exe_paths["vmd"],
                            shade_mode=shade_mode, keep_h_indices=keep_h_indices)
                        if port:
                            self.vmd_port = port
                            self.vmd_render_dir = render_dir
                            # 记录原始 log 路径（用于输出命名）
                            self.vmd_xyz_path = xyz_file
                            self.btn_run.config(state="normal")
                            self.btn_render.config(state="normal")
                            self.btn_draw_bond.config(state="normal")
                            self._append(f"VMD 已启动 (端口 {port})")
                            self._poll_pick_file()
                        else:
                            self._append("VMD 启动失败")
                    except Exception as e:
                        self._append(f"VMD 启动错误: {e}")
                elif auto:
                    # 自动模式：逐个渲染 xyz
                    self._append(f"\n[步骤2] 自动渲染 {len(xyz_files)} 个文件")
                    for i, xyz_file in enumerate(xyz_files):
                        if not self.running:
                            self._append("已停止"); break
                        name = os.path.basename(xyz_file)
                        stem = os.path.splitext(name)[0]
                        self.var_prog.set(f"[渲染 {i+1}/{len(xyz_files)}] {name}")
                        self._append(f"\n[渲染 {i+1}/{len(xyz_files)}] {name}")

                        t0 = time.time()
                        png = os.path.join(out, f"{stem}.png")
                        try:
                            result = render_mol_auto(
                                xyz_file, output_png=png,
                                style_name=style_name,
                                representation=representation,
                                cpk_scale=str(cpk_scale),
                                resolution=resolution,
                                vmd_exe=exe_paths["vmd"],
                                tachyon_exe=exe_paths["tachyon"],
                                shade_mode=shade_mode,
                                keep_h_indices=keep_h_indices)
                            dt = time.time() - t0
                            if result:
                                self._append(f"  PNG: {os.path.basename(result)} ({dt:.1f}s)")
                                ok += 1
                            else:
                                self._append(f"  渲染失败 ({dt:.1f}s)")
                        except Exception as e:
                            self._append(f"  错误: {e}")

                    elapsed = time.time() - t_total
                    self._append(f"\n全部完成: {ok}/{len(xyz_files)}，耗时 {elapsed:.1f}s")
                    self.var_prog.set(f"完成: {ok}/{len(xyz_files)}")
                    if do_open and ok > 0:
                        os.startfile(out)

                self.running = False
                self.btn_run.config(state="normal")
                self.btn_stop.config(state="disabled")

            threading.Thread(target=worker, daemon=True).start()

        def _preview(self):
            """预览指定 log 文件（先转 xyz，再 VMD 预览）"""
            path = self.var_path.get().strip()
            if not path:
                return

            log_file = path if os.path.isfile(path) else None
            if not log_file:
                out = self.var_out.get().strip()
                if out:
                    logs = sorted(glob.glob(os.path.join(out, "*.log")))
                    if logs:
                        log_file = logs[-1]

            if not log_file:
                messagebox.showwarning("提示", "请选择 .log 文件")
                return

            out = self.var_out.get().strip() or (
                path if os.path.isdir(path) else os.path.dirname(path))
            exe_paths = self._get_paths()
            style_name, representation, cpk_scale, resolution, shade_mode, keep_h_indices = self._get_params()
            
            # 保存当前样式参数用于后续重新加载
            self.vmd_style_name = style_name
            self.vmd_representation = representation
            self.vmd_cpk_scale = cpk_scale
            self.vmd_shade_mode = shade_mode
            # 计算并缓存 rep_style / rep_material，供 _toggle_h_filter 使用
            _s = STYLES.get(style_name, STYLES["sob-art"])
            _atom_cpk = _s.get("atom_cpk", "0.600000 0.400000 30.000000 30.000000")
            
            # 应用 cpk_scale 缩放因子
            _cpk_parts = _atom_cpk.split()
            if len(_cpk_parts) >= 2:
                try:
                    _scale_factor = float(cpk_scale)
                    _new_sphere = float(_cpk_parts[0]) * _scale_factor
                    _new_bond = float(_cpk_parts[1]) * _scale_factor
                    _scaled_cpk = f"{_new_sphere:.6f} {_new_bond:.6f}"
                    if len(_cpk_parts) >= 4:
                        _scaled_cpk += f" {_cpk_parts[2]} {_cpk_parts[3]}"
                    _atom_cpk = _scaled_cpk
                except (ValueError, IndexError):
                    pass
            
            if representation == "CPK":
                self._current_rep_style = f"CPK {_atom_cpk}"
                self._current_rep_material = "_stl_atom"
            elif representation == "Licorice":
                self._current_rep_style = "Licorice 0.2 12 12"
                self._current_rep_material = "_stl_bond"
            elif representation == "VDW":
                self._current_rep_style = f"VDW {_atom_cpk.split()[0]} 12"
                self._current_rep_material = "_stl_atom"
            elif representation == "Bonds":
                self._current_rep_style = "Bonds 0.3 12"
                self._current_rep_material = "_stl_bond"
            else:
                self._current_rep_style = "Lines 1.0"
                self._current_rep_material = "_stl_atom"

            # 先转 xyz
            self._append(f"\n[1] Multiwfn: log -> xyz  ({os.path.basename(log_file)})")
            xyz = log_to_xyz(log_file,
                             multiwfn_exe=exe_paths["multiwfn"],
                             work_dir=out)
            if not xyz:
                self._append("  xyz 转换失败！")
                return
            self._append(f"  -> {os.path.basename(xyz)}")

            # VMD 预览 xyz
            self._append(f"[2] 启动 VMD 预览: {os.path.basename(xyz)}")
            self._append(f"样式: {style_name}  表示: {representation}")

            try:
                port, render_dir = preview_mol(
                    xyz, style_name=style_name,
                    representation=representation, cpk_scale=str(cpk_scale),
                    vmd_exe=exe_paths["vmd"],
                    shade_mode=shade_mode, keep_h_indices=keep_h_indices)
                if port:
                    self.vmd_port = port
                    self.vmd_render_dir = render_dir
                    self.vmd_xyz_path = xyz
                    self.btn_run.config(state="normal")
                    self.btn_render.config(state="normal")
                    self.btn_draw_bond.config(state="normal")
                    self._append(f"VMD 已启动 (端口 {port})，等待操作...")
                else:
                    self._append("VMD 启动失败")
            except Exception as e:
                self._append(f"VMD 启动错误: {e}")

        def _render_view(self):
            """通过 socket 向 VMD 发送渲染命令"""
            if not self.vmd_port or not self.vmd_render_dir:
                messagebox.showwarning("提示", "请先点击 [VMD预览] 打开 VMD")
                return

            out = self.var_out.get().strip()
            if out and not os.path.isdir(out):
                os.makedirs(out, exist_ok=True)

            style_name, _, _, resolution, shade_mode, _ = self._get_params()
            exe_paths = self._get_paths()

            # 输出文件名与 xyz 一致（xyz 名字和 log 去掉扩展名一致）
            output_png = None
            if self.vmd_xyz_path and out:
                stem = os.path.splitext(os.path.basename(self.vmd_xyz_path))[0]
                output_png = os.path.join(out, f"{stem}.png")

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

        def _send_vmd(self, cmd):
            if not self.vmd_port:
                self._append("VMD 未连接")
                return False
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(3)
                s.connect(("127.0.0.1", self.vmd_port))
                s.sendall((cmd + "\n").encode("utf-8"))
                time.sleep(0.2)
                resp = b""
                try:
                    while True:
                        chunk = s.recv(4096)
                        if not chunk:
                            break
                        resp += chunk
                        if b"\n" in resp:
                            break
                except socket.timeout:
                    pass
                s.close()
                return True
            except Exception as e:
                self._append(f"VMD 通信失败: {e}")
                return False

        def _draw_bond(self):
            if not self.vmd_port:
                messagebox.showwarning("提示", "请先预览打开 VMD")
                return
            a1 = self.var_ba1.get().strip()
            a2 = self.var_ba2.get().strip()
            if not a1 or not a2:
                messagebox.showwarning("提示", "请输入两个原子索引")
                return
            color = self.bond_colors.get(self.var_bcolor.get(), "gray")
            btype = self.bond_types.get(self.var_btype.get(), "dots")
            mat = self.bond_mats.get(self.var_bmat.get(), "HalfTransparent")
            nbars = self.var_bnbars.get().strip() or "10"
            space = self.var_bspace.get().strip() or "1.2"
            radius = self.var_bradius.get().strip() or "0.06"
            if btype == "cylinder":
                cmd = (f"draw_bond -mol1 top -index1 {a1} -mol2 top -index2 {a2} "
                       f"-color {color} -h_type {btype} -h_radius {radius} -mat {mat}")
            else:
                cmd = (f"draw_bond -mol1 top -index1 {a1} -mol2 top -index2 {a2} "
                       f"-h_nbars {nbars} -h_space {space} -h_radius {radius} "
                       f"-color {color} -h_type {btype} -mat {mat}")
            ok = self._send_vmd(cmd)
            if ok:
                self._append(f"画虚线: 原子{a1}-{a2} {color} {btype} {mat}")
                self.btn_undo_bond.config(state="normal")

        def _undo_bond(self):
            self._send_vmd("draw_bond_undo")
            self._append("撤销上一条虚线")

        def _clear_bonds(self):
            self._send_vmd("draw_bond_clear")
            self._append("清除全部虚线")
            self.btn_undo_bond.config(state="disabled")

        def _stop(self):
            self.running = False
            self.btn_stop.config(state="disabled")

    root = tk.Tk()
    App(root)
    root.mainloop()


# ── 命令行入口 ────────────────────────────────────────────
def main():
    if len(sys.argv) > 1:
        import argparse
        p = argparse.ArgumentParser(description="Multiwfn + VMD/Tachyon 分子结构渲染 v1.1 (Gaussian log)")
        p.add_argument("input", help="log 文件或文件夹")
        p.add_argument("--style", default="sob_Gold",
                       choices=list(STYLES.keys()), help="渲染样式")
        p.add_argument("--rep", default="CPK",
                       choices=list(REPRESENTATIONS.keys()), help="分子表示方式")
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
            # log -> xyz
            xyz = log_to_xyz(f, work_dir=out)
            if not xyz:
                print("  log->xyz 失败")
                continue
            print(f"  xyz: {os.path.basename(xyz)}")
            # xyz -> PNG
            stem = os.path.splitext(os.path.basename(f))[0]
            png = os.path.join(out, f"{stem}.png")
            result = render_mol_auto(xyz, output_png=png,
                                     style_name=a.style,
                                     representation=a.rep,
                                     cpk_scale=str(a.scale),
                                     resolution=(w, h))
            if result:
                print(f"  OK: {os.path.basename(result)}")
            else:
                print(f"  渲染失败")
    else:
        launch_gui()


if __name__ == "__main__":
    main()
