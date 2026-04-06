"""
Custom build that compiles libMarvinSDK.so and libKine.so,
then places them inside SDK_PYTHON (the marvin_sdk package)
so setuptools picks them up as package-data.
"""

import os
import subprocess
import glob
import shutil
from setuptools import setup
from setuptools.command.build_py import build_py

# Use the directory containing this file as root.
# In an isolated build (pixi/uv) this will be the unpacked sdist.
ROOT = os.path.dirname(os.path.abspath(__file__))
PKG_DIR = os.path.join(ROOT, "SDK_PYTHON")
LIB_DIR = os.path.join(ROOT, "lib")

import sys
import platform

IS_MACOS = sys.platform == "darwin"

CXX = os.environ.get("CXX", "clang++" if IS_MACOS else "g++")
CXXFLAGS = ["-Wall", "-w", "-O2", "-fPIC", "-shared", "-std=c++17"]

CONTRL_SRCS = None  # will glob at build time

if IS_MACOS:
    LIBS = ["-lpthread"]
    CMPL_FLAG = "-DCMPL_MAC"
    EXTRA_FLAGS = ["-DUSE_SINGLE_SOCK"]
    LIB_EXT = ".dylib"
else:
    LIBS = ["-lpthread", "-lrt"]
    CMPL_FLAG = "-DCMPL_LIN"
    EXTRA_FLAGS = []
    LIB_EXT = ".so"

SYMLINK_DIRS = ("SDK_PYTHON", "DEMO_C++", "DEMO_PYTHON", "contrlSDK", "kinematicsSDK")


def compile_lib(name, src_dir, sources, extra_flags=None):
    """Compile a shared library into lib/ and copy into SDK_PYTHON/."""
    os.makedirs(LIB_DIR, exist_ok=True)
    out = os.path.join(LIB_DIR, name)
    srcs = [os.path.join(ROOT, src_dir, s) for s in sources]

    # Verify sources exist
    for s in srcs:
        if not os.path.isfile(s):
            raise FileNotFoundError(
                f"C++ source not found: {s}\n"
                f"  ROOT={ROOT}\n"
                f"  cwd={os.getcwd()}\n"
                f"  contents={os.listdir(ROOT)}"
            )

    cmd = [CXX] + CXXFLAGS + (extra_flags or []) + srcs + ["-o", out] + LIBS
    print(f"  compiling {name} ...")
    subprocess.check_call(cmd)

    # Copy .so into the package dir so setuptools includes it
    dest = os.path.join(PKG_DIR, name)
    if os.path.lexists(dest):
        os.remove(dest)
    shutil.copy2(out, dest)


def refresh_symlinks():
    """Symlink lib/*.so into legacy consumer directories (skip in isolated builds)."""
    for dest in SYMLINK_DIRS:
        dest_dir = os.path.join(ROOT, dest)
        if not os.path.isdir(dest_dir):
            continue
        for lib in ("libMarvinSDK" + LIB_EXT, "libKine" + LIB_EXT):
            link = os.path.join(dest_dir, lib)
            target = os.path.join(LIB_DIR, lib)
            if os.path.lexists(link):
                os.remove(link)
            # Use copy in case symlinks aren't supported (isolated builds)
            try:
                os.symlink(target, link)
            except OSError:
                shutil.copy2(target, link)


class BuildAndCopy(build_py):
    """Compile the C++ shared libs before collecting Python packages."""

    def run(self):
        contrl_srcs = [
            os.path.basename(p)
            for p in glob.glob(os.path.join(ROOT, "contrlSDK", "*.cpp"))
        ]
        compile_lib(
            "libMarvinSDK" + LIB_EXT, "contrlSDK", contrl_srcs,
            extra_flags=[CMPL_FLAG] + EXTRA_FLAGS,
        )
        kine_srcs = [
            os.path.basename(p)
            for p in glob.glob(os.path.join(ROOT, "kinematicsSDK", "*.cpp"))
        ]
        compile_lib("libKine" + LIB_EXT, "kinematicsSDK", kine_srcs)
        refresh_symlinks()
        super().run()


setup(
    name="marvin_robot",
    version="0.1.0",
    packages=["marvin_robot"],
    package_dir={"marvin_robot": "SDK_PYTHON"},
    package_data={"marvin_robot": ["*.so", "*.dylib", "*.dll"]},
    cmdclass={"build_py": BuildAndCopy},
)
