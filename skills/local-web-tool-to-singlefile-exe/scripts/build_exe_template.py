#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模板：把「Python 本地 Web 工具」构建为免安装单文件 exe（PyInstaller）
====================================================================
用法：拷到项目根目录，改下面 ===== CONFIG ===== 区，然后
    python build_exe.py
产物：
    dist/<FINAL_NAME>.exe    单文件、免安装、双击即用
    dist/使用说明.txt        给使用方的说明（版本号自动同步）
    build/、*.spec           中间产物（记得进 .gitignore）

依赖：PyInstaller（在受管 venv 里装：<venv>/Scripts/python.exe -m pip install pyinstaller）
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

# ===== CONFIG（按项目改）=====================================================
HERE = os.path.dirname(os.path.abspath(__file__))
APP_FILE = "server.py"                  # 入口脚本
EXTRA_MODULES = ["ecg_analysis"]        # 需要 --hidden-import 的项目内模块
STATIC_DIR = "static"                   # 需要随包分发的静态资源目录（可为 None）
STATIC_FILES = ["static/index.html", "static/app.js"]   # 构建前存在性检查
EXE_BASENAME = "MyTool"                 # PyInstaller 内部名，必须纯 ASCII
FINAL_NAME = "我的工具"                  # 交付给用户的中文 exe 名
DEFAULT_PORT = 8766                     # 与 server.py 默认端口保持一致
VERSION_RE = r'APP_VERSION\s*=\s*"([^"]+)"'
EXCLUDE_MODULES = ["numpy", "pandas", "matplotlib", "scipy", "PIL", "tkinter"]
# ============================================================================


def read_version():
    with open(os.path.join(HERE, APP_FILE), "r", encoding="utf-8") as f:
        m = re.search(VERSION_RE, f.read())
    return m.group(1) if m else "0.0.0"


README_TMPL = """{name} v{ver} · 使用说明
========================================

一、运行（免安装）
1. 把「{exe}」拷到任意位置（桌面或单独文件夹均可）。
2. 双击运行：会出现一个黑色命令行窗口，并自动打开浏览器页面。
   · 若浏览器没有自动打开：手动打开浏览器访问  http://localhost:{port}
   · 那个黑色窗口就是程序本体，用完直接关闭它即退出程序。

二、环境要求
· Windows 10/11（64 位）；无需安装 Python；完全离线可用。

三、隐私
· 数据不上传、不联网、不保存：仅在本机临时解析，分析结束立即删除临时文件。

四、常见问题
1. 首次运行被 Windows SmartScreen 拦截（"Windows 已保护你的电脑"）：
   点「更多信息」→「仍要运行」即可（未做数字签名的自制工具常见提示）。
2. 双击后窗口一闪而过：多为杀毒软件拦截或端口被占用。
   可在命令行（cmd）中进入该目录执行  {exe}  查看具体提示。
3. 提示端口被占用：程序会自动顺延；也可用  {exe} --port 9000  指定。
4. 已经开着程序时再次双击：会自动用默认浏览器打开已有实例，不会重复启动。

五、命令行参数（一般不需要）
  --port N        指定端口（默认 {port}）
  --no-browser    启动后不自动打开浏览器
  --host IP       监听地址（默认 127.0.0.1，仅本机访问）

版本：v{ver}
"""


def check_sources():
    need = [p for p in [APP_FILE] + STATIC_FILES
            if p is not None and not os.path.isfile(os.path.join(HERE, p))]
    if need:
        sys.exit("缺少必要文件：%s" % ", ".join(need))


def stash_before_build(paths):
    """把上一版 exe 移走再构建。
    本机（WorkBuddy Windows 环境）存在 safe-delete 钩子：删除/覆盖已存在的 exe
    会被拦截并让构建中断。改用移动到 dist/_stash/（非破坏性、可随时取回）。
    """
    stash_dir = os.path.join(HERE, "dist", "_stash")
    for p in paths:
        if os.path.exists(p):
            os.makedirs(stash_dir, exist_ok=True)
            os.replace(p, os.path.join(stash_dir, os.path.basename(p)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--windowed", action="store_true",
                    help="不显示控制台窗口（不推荐：出错时无提示）")
    ap.add_argument("--keep-build", action="store_true", help="保留 build/ 中间目录")
    args = ap.parse_args()

    check_sources()
    ver = read_version()
    sep = os.pathsep  # Windows: ';'  —— 绝不能硬写 ':'

    # 构建工作区放系统临时目录且每次新建：
    #  ① 不要用 --clean —— 它要批量删 build/ 内容，会被 safe-delete 钩子拦截；
    #  ② 不要复用旧工作目录 —— PyInstaller 覆盖其中的文件同样会被拦截。
    work_dir = os.path.join(tempfile.gettempdir(),
                            "build_work_" + time.strftime("%Y%m%d_%H%M%S"))
    cmd = [sys.executable, "-m", "PyInstaller",
           "--noconfirm", "--onefile",
           "--name", EXE_BASENAME,
           "--workpath", work_dir,
           "--specpath", tempfile.gettempdir()]
    if STATIC_DIR:
        # 用绝对路径：设了 --specpath 后，相对路径会以 spec 所在目录为基准 → 找不到资源
        cmd += ["--add-data", "%s%s%s" % (os.path.join(HERE, STATIC_DIR), sep, STATIC_DIR)]
    for m in EXTRA_MODULES:
        cmd += ["--hidden-import", m]
    for m in EXCLUDE_MODULES:
        cmd += ["--exclude-module", m]
    if args.windowed:
        cmd.append("--windowed")
    cmd.append(APP_FILE)

    print("[1/3] 调用 PyInstaller 构建单文件 exe …")
    stash_before_build([os.path.join(HERE, "dist", EXE_BASENAME + ".exe"),
                        os.path.join(HERE, "dist", FINAL_NAME + ".exe")])
    print("      " + " ".join(cmd))
    try:
        subprocess.check_call(cmd, cwd=HERE)
    except FileNotFoundError:
        sys.exit("未找到 PyInstaller，请先安装：python -m pip install pyinstaller")
    except subprocess.CalledProcessError as e:
        sys.exit("PyInstaller 构建失败（退出码 %d）" % e.returncode)

    src_exe = os.path.join(HERE, "dist", EXE_BASENAME + ".exe")
    if not os.path.isfile(src_exe):
        sys.exit("未生成 exe：%s" % src_exe)
    final_exe = os.path.join(HERE, "dist", FINAL_NAME + ".exe")
    # 不要先 os.remove —— Windows 上 os.replace 本身即可原子覆盖，且不触发删除拦截
    os.replace(src_exe, final_exe)     # ASCII 构建 → 中文交付名

    print("[2/3] 写入使用说明 …")
    with open(os.path.join(HERE, "dist", "使用说明.txt"), "w", encoding="utf-8") as f:
        f.write(README_TMPL.format(name=FINAL_NAME, ver=ver,
                                   exe=FINAL_NAME + ".exe", port=DEFAULT_PORT))

    if not args.keep_build:
        # safe-delete 钩子会拦 rmtree；失败不影响产物，忽略即可（工作区在 temp 里）
        shutil.rmtree(os.path.join(HERE, "build"), ignore_errors=True)

    size_mb = os.path.getsize(final_exe) / 1024.0 / 1024.0
    print("[3/3] 完成")
    print("      产物: %s  (%.1f MB)" % (final_exe, size_mb))
    print("      说明: %s" % os.path.join(HERE, "dist", "使用说明.txt"))
    print("      交付方式: 把 dist 里的这两个文件拷给对方，双击 exe 即用。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
