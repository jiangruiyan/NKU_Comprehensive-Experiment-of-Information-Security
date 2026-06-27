"""
构建并打包 Zygisk Envoy Mod

使用方式:
  python build.py              # 自动查找 NDK, 编译, 打包
  python build.py --ndk /path  # 指定 NDK 路径
  python build.py --pack-only  # 仅打包 (已编译过)

前置条件:
  - Android NDK r21+ (下载: https://developer.android.com/ndk/downloads)
  - 设置 ANDROID_NDK_ROOT 环境变量, 或用 --ndk 参数指定

输出:
  zygisk_envoy_mod.zip — 直接在 Magisk 中刷入即可
"""

import os
import sys
import shutil
import zipfile
import argparse
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
MODULE_DIR = SCRIPT_DIR
JNI_DIR = MODULE_DIR / "jni"
BUILD_OUTPUT = MODULE_DIR / "libs" / "armeabi-v7a"
ZIP_NAME = "zygisk_envoy_mod.zip"


def find_ndk(ndk_arg: str = None) -> Path:
    """查找 Android NDK 路径"""
    candidates = []
    if ndk_arg:
        candidates.append(Path(ndk_arg))
    if os.environ.get("ANDROID_NDK_ROOT"):
        candidates.append(Path(os.environ["ANDROID_NDK_ROOT"]))
    if os.environ.get("ANDROID_NDK_HOME"):
        candidates.append(Path(os.environ["ANDROID_NDK_HOME"]))
    if os.environ.get("NDK_HOME"):
        candidates.append(Path(os.environ["NDK_HOME"]))

    # 常见 Windows 安装路径
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    if local_appdata:
        sdk_ndk = Path(local_appdata) / "Android" / "Sdk" / "ndk"
        if sdk_ndk.exists():
            # 取最新版本
            versions = sorted(sdk_ndk.iterdir(), reverse=True)
            if versions:
                candidates.append(versions[0])

    for c in candidates:
        ndk_build = c / "ndk-build.cmd" if sys.platform == "win32" else c / "ndk-build"
        if ndk_build.exists():
            return c
    return None


def run_ndk_build(ndk_path: Path):
    """执行 ndk-build 编译"""
    ndk_build = ndk_path / ("ndk-build.cmd" if sys.platform == "win32" else "ndk-build")

    print(f"[*] NDK path: {ndk_path}")
    print(f"[*] Building native library...")

    cmd = [
        str(ndk_build),
        f"NDK_PROJECT_PATH={MODULE_DIR}",
        f"NDK_APPLICATION_MK={JNI_DIR / 'Application.mk'}",
        f"APP_BUILD_SCRIPT={JNI_DIR / 'Android.mk'}",
        f"NDK_OUT={MODULE_DIR / 'obj'}",
        f"NDK_LIBS_OUT={MODULE_DIR / 'libs'}",
        "-j4",
    ]

    result = subprocess.run(cmd, cwd=str(MODULE_DIR),
                            capture_output=True, text=True, errors='replace')
    print(result.stdout)
    if result.returncode != 0:
        print("[!] Build FAILED:")
        print(result.stderr)
        sys.exit(1)

    so_path = BUILD_OUTPUT / "libzygisk_envoy.so"
    if not so_path.exists():
        print(f"[!] Output not found: {so_path}")
        sys.exit(1)

    print(f"[+] Build OK: {so_path} ({so_path.stat().st_size:,} bytes)")
    return so_path


def package_module(so_path: Path):
    """打包为 Magisk 模块 zip"""
    zip_path = MODULE_DIR / ZIP_NAME

    print(f"[*] Packaging module -> {zip_path}")

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # module.prop
        zf.write(MODULE_DIR / "module.prop", "module.prop")

        # Zygisk 模块: 将 .so 放到 zygisk/<abi>.so
        # Zygisk 会自动加载 zygisk/ 目录下以 ABI 命名的 .so
        zf.write(so_path, "zygisk/armeabi-v7a.so")

    print(f"[+] Package OK: {zip_path} ({zip_path.stat().st_size:,} bytes)")
    print()
    print("=" * 60)
    print("  安装方法:")
    print("  1. 将 zygisk_envoy_mod.zip 传到手机")
    print("  2. 打开 Magisk -> 模块 -> 从本地安装")
    print("  3. 选择 zygisk_envoy_mod.zip")
    print("  4. 重启设备")
    print("  5. 启动元气骑士, 选择古代元素使进入游戏")
    print()
    print("  查看日志: adb logcat -s EnvoyMod:*")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Build Zygisk Envoy Mod")
    parser.add_argument("--ndk", help="Android NDK path")
    parser.add_argument("--pack-only", action="store_true",
                        help="Skip build, only package (requires previous build)")
    args = parser.parse_args()

    so_path = BUILD_OUTPUT / "libzygisk_envoy.so"

    if not args.pack_only:
        ndk = find_ndk(args.ndk)
        if ndk is None:
            print("[!] Android NDK not found!")
            print("    请设置 ANDROID_NDK_ROOT 环境变量或使用 --ndk 参数")
            print("    下载: https://developer.android.com/ndk/downloads")
            sys.exit(1)
        so_path = run_ndk_build(ndk)
    else:
        if not so_path.exists():
            print(f"[!] {so_path} not found. Run build first (without --pack-only)")
            sys.exit(1)

    package_module(so_path)


if __name__ == "__main__":
    main()
