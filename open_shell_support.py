#!/usr/bin/env python3
"""
开壳层轨道编号支持模块
检测fchk文件是否为开壳层体系，并提供alpha/beta轨道选择功能
"""

import os

def is_open_shell(fchk_path):
    """
    检测fchk文件是否为开壳层体系
    
    返回值:
    - None: 无法确定
    - "closed": 闭壳层 (RHF)
    - "open": 开壳层 (UHF/ROHF)
    """
    try:
        with open(fchk_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read().lower()
            
        # 检测开壳层特征
        # UHF特征: "number of alpha electrons" 和 "number of beta electrons"
        # ROHF特征: 也会有alpha/beta电子数但不相等
        if 'number of alpha electrons' in content and 'number of beta electrons' in content:
            # 解析alpha和beta电子数
            import re
            alpha_match = re.search(r'number of alpha electrons\s+(\d+)', content)
            beta_match = re.search(r'number of beta electrons\s+(\d+)', content)
            
            if alpha_match and beta_match:
                alpha = int(alpha_match.group(1))
                beta = int(beta_match.group(1))
                if alpha != beta:
                    return "open"
        
        # 检测闭壳层特征
        if 'total number of electrons' in content and 'number of alpha electrons' not in content:
            return "closed"
        
        # 默认假设为闭壳层
        return "closed"
        
    except Exception:
        return None


def gen_cube_open_shell(fchk_path, orbital="h", grid_quality=2, spin="alpha",
                        multiwfn_exe=None, work_dir=None):
    """
    为开壳层体系生成轨道cube文件
    
    参数:
    - fchk_path: fchk文件路径
    - orbital: 轨道编号或标识 (h/l/h-1/数字)
    - grid_quality: 网格质量 (1-5)
    - spin: "alpha" 或 "beta"
    - multiwfn_exe: Multiwfn可执行文件路径
    - work_dir: 工作目录
    
    返回: cube文件路径或None
    """
    if multiwfn_exe is None:
        multiwfn_exe = r"E:\Multiwfn_2026.4.10_bin_Win64\Multiwfn.exe"
    if work_dir is None:
        work_dir = os.path.dirname(os.path.abspath(fchk_path))
    os.makedirs(work_dir, exist_ok=True)

    fchk_name = os.path.basename(fchk_path)
    ascii_dir = os.path.join(work_dir, "_multiwfn_tmp")
    os.makedirs(ascii_dir, exist_ok=True)
    ascii_fchk = os.path.join(ascii_dir, fchk_name)
    if not os.path.exists(ascii_fchk):
        import shutil
        shutil.copy2(fchk_path, ascii_fchk)

    # 开壳层体系的Multiwfn命令序列:
    # 5 -> 1(alpha)或2(beta) -> 4 -> 轨道号 -> 网格质量 -> 2 -> 0 -> q
    spin_code = "1" if spin == "alpha" else "2"
    
    inputs = (
        "\n" + fchk_name + "\n5\n" + spin_code + "\n4\n" + orbital + "\n"
        + str(grid_quality) + "\n2\n0\nq\n"
    )

    try:
        import subprocess
        subprocess.run(
            multiwfn_exe, input=inputs, capture_output=True,
            cwd=ascii_dir, timeout=600, encoding="utf-8", errors="replace",
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"  Error: {e}")
        return None

    cube_src = os.path.join(ascii_dir, "MOvalue.cub")
    if not os.path.exists(cube_src):
        return None

    stem = os.path.splitext(fchk_name)[0]
    # 开壳层轨道文件名加入spin标识
    cube_dst = os.path.join(work_dir, f"{stem}_MO{orbital}_{spin[0]}.cub")
    shutil.move(cube_src, cube_dst)
    try:
        shutil.rmtree(ascii_dir)
    except OSError:
        pass
    return cube_dst


def gen_cube_closed_shell(fchk_path, orbital="h", grid_quality=2,
                          multiwfn_exe=None, work_dir=None):
    """
    为闭壳层体系生成轨道cube文件（原有逻辑）
    
    参数:
    - fchk_path: fchk文件路径
    - orbital: 轨道编号或标识 (h/l/h-1/数字)
    - grid_quality: 网格质量 (1-5)
    - multiwfn_exe: Multiwfn可执行文件路径
    - work_dir: 工作目录
    
    返回: cube文件路径或None
    """
    if multiwfn_exe is None:
        multiwfn_exe = r"E:\Multiwfn_2026.4.10_bin_Win64\Multiwfn.exe"
    if work_dir is None:
        work_dir = os.path.dirname(os.path.abspath(fchk_path))
    os.makedirs(work_dir, exist_ok=True)

    fchk_name = os.path.basename(fchk_path)
    ascii_dir = os.path.join(work_dir, "_multiwfn_tmp")
    os.makedirs(ascii_dir, exist_ok=True)
    ascii_fchk = os.path.join(ascii_dir, fchk_name)
    if not os.path.exists(ascii_fchk):
        import shutil
        shutil.copy2(fchk_path, ascii_fchk)

    # 闭壳层体系的Multiwfn命令序列:
    # 5 -> 4 -> 轨道号 -> 网格质量 -> 2 -> 0 -> q
    inputs = (
        "\n" + fchk_name + "\n5\n4\n" + orbital + "\n"
        + str(grid_quality) + "\n2\n0\nq\n"
    )

    try:
        import subprocess
        subprocess.run(
            multiwfn_exe, input=inputs, capture_output=True,
            cwd=ascii_dir, timeout=600, encoding="utf-8", errors="replace",
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"  Error: {e}")
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


def gen_cube_auto(fchk_path, orbital="h", grid_quality=2, spin=None,
                  multiwfn_exe=None, work_dir=None):
    """
    自动检测并生成轨道cube文件
    
    参数:
    - fchk_path: fchk文件路径
    - orbital: 轨道编号或标识 (h/l/h-1/数字)
    - grid_quality: 网格质量 (1-5)
    - spin: None=自动检测, "alpha"=alpha轨道, "beta"=beta轨道
    - multiwfn_exe: Multiwfn可执行文件路径
    - work_dir: 工作目录
    
    返回: (cube文件路径, spin类型) 或 (None, None)
    """
    shell_type = is_open_shell(fchk_path)
    
    if shell_type == "open":
        # 开壳层体系
        if spin is None:
            # 默认使用alpha轨道
            spin = "alpha"
        cube_path = gen_cube_open_shell(fchk_path, orbital, grid_quality, spin,
                                       multiwfn_exe, work_dir)
        return cube_path, spin
    else:
        # 闭壳层体系或无法确定
        cube_path = gen_cube_closed_shell(fchk_path, orbital, grid_quality,
                                         multiwfn_exe, work_dir)
        return cube_path, None


if __name__ == "__main__":
    # 测试示例
    test_fchk = r"path\to\your\molecule.fchk"
    if os.path.exists(test_fchk):
        shell_type = is_open_shell(test_fchk)
        print(f"Shell type: {shell_type}")
        
        if shell_type == "open":
            # 生成alpha轨道
            cube_a, _ = gen_cube_auto(test_fchk, "h", spin="alpha")
            print(f"Alpha HOMO: {cube_a}")
            
            # 生成beta轨道
            cube_b, _ = gen_cube_auto(test_fchk, "h", spin="beta")
            print(f"Beta HOMO: {cube_b}")
        else:
            cube, _ = gen_cube_auto(test_fchk, "h")
            print(f"HOMO: {cube}")
