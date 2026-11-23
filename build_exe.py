# -*- coding: utf-8 -*-
"""一键打包成单文件 exe（中文名称全部写在这里，避免批处理编码问题）。"""
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)
PY = sys.executable
APP = "PHB法术检索器"


def run(args):
    print(">>", " ".join(args))
    return subprocess.call(args)


def need_pyinstaller():
    try:
        import PyInstaller  # noqa: F401
        return False
    except ImportError:
        return True


def main():
    print("=" * 52)
    print("  PHB 法术检索器 · 重新打包")
    print("=" * 52)
    print("Python:", PY)

    if need_pyinstaller():
        print("\n[1/4] 安装 PyInstaller …")
        if run([PY, "-m", "pip", "install", "--upgrade", "pyinstaller"]) != 0:
            print("\n[错误] PyInstaller 安装失败，请检查网络。")
            return 1
    else:
        print("\n[1/4] PyInstaller 已就绪")

    print("\n[2/4] 重新生成数据模块 spells_data.py …")
    if os.path.exists("spells.json"):
        if run([PY, "make_data_module.py"]) != 0:
            print("\n[错误] 数据模块生成失败。")
            return 1
    else:
        print("    跳过：没有 spells.json")

    print("\n[3/4] 检查图标 …")
    if not os.path.exists("app.ico"):
        if run([PY, "make_icon.py"]) != 0:
            print("    [警告] 图标生成失败，将使用默认图标")
    else:
        print("    app.ico 已存在")

    print("\n[4/4] 打包 exe …")
    args = [PY, "-m", "PyInstaller", "--noconfirm", "--onefile", "--windowed",
            "--name", APP, "--icon", os.path.join(BASE, "app.ico"),
            "--add-data", os.path.join(BASE, "app.ico") + ";.",
            "--distpath", os.path.abspath(os.path.join(BASE, "..")),
            "--workpath", os.path.join(BASE, "build"),
            "--specpath", os.path.join(BASE, "build"),
            os.path.join(BASE, "phb_app.py")]
    if run(args) != 0:
        print("\n[错误] 打包失败，请把上面的日志发给我。")
        return 1

    out = os.path.join(BASE, "..", APP + ".exe")
    print("\n完成：%s" % os.path.normpath(out))
    if os.path.exists(out):
        print("大小：%.1f MB" % (os.path.getsize(out) / 1024 / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
