"""
Custom build that compiles libMarvinSDK.so and libKine.so,
then places them inside SDK_PYTHON (the marvin_sdk package)
so setuptools picks them up as package-data.
"""

import os
import subprocess
import glob
from setuptools import setup
from setuptools.command.build_py import build_py

ROOT = os.path.dirname(os.path.abspath(__file__))
PKG_DIR = os.path.join(ROOT, "SDK_PYTHON")
LIB_DIR = os.path.join(ROOT, "lib")

CXX = os.environ.get("CXX", "g++")
CXXFLAGS = ["-Wall", "-w", "-O2", "-fPIC", "-shared", "-std=c++17"]

CONTRL_SRCS = [
    "MarvinSDK.cpp", "Robot.cpp", "ACB.cpp", "FXDG.cpp", "PointSet.cpp",
    "FileOP.cpp", "FilePortal.cpp", "Parser.cpp", "TCPAgent.cpp", "TCPFileClient.cpp",
]

LIBS = ["-lpthread", "-lrt"]

SYMLINK_DIRS = ("SDK_PYTHON", "DEMO_C++", "DEMO_PYTHON", "contrlSDK", "kinematicsSDK")


def compile_lib(name, src_dir, sources, extra_flags=None):
    """Compile a shared library into lib/."""
    os.makedirs(LIB_DIR, exist_ok=True)
    out = os.path.join(LIB_DIR, name)
    srcs = [os.path.join(ROOT, src_dir, s) for s in sources]
    cmd = [CXX] + CXXFLAGS + (extra_flags or []) + srcs + ["-o", out] + LIBS
    print(f"  compiling {name} ...")
    subprocess.check_call(cmd)


def refresh_symlinks():
    """Symlink lib/*.so into every consumer directory."""
    for dest in SYMLINK_DIRS:
        dest_dir = os.path.join(ROOT, dest)
        if not os.path.isdir(dest_dir):
            continue
        for lib in ("libMarvinSDK.so", "libKine.so"):
            link = os.path.join(dest_dir, lib)
            target = os.path.join(LIB_DIR, lib)
            if os.path.lexists(link):
                os.remove(link)
            os.symlink(target, link)


class BuildAndCopy(build_py):
    """Compile the C++ shared libs before collecting Python packages."""

    def run(self):
        compile_lib(
            "libMarvinSDK.so", "contrlSDK", CONTRL_SRCS,
            extra_flags=["-DCMPL_LIN"],
        )
        kine_srcs = [
            os.path.basename(p)
            for p in glob.glob(os.path.join(ROOT, "kinematicsSDK", "*.cpp"))
        ]
        compile_lib("libKine.so", "kinematicsSDK", kine_srcs)
        refresh_symlinks()
        super().run()


setup(
    packages=["marvin_sdk"],
    package_dir={"marvin_sdk": "SDK_PYTHON"},
    package_data={"marvin_sdk": ["*.so", "*.dll"]},
    cmdclass={"build_py": BuildAndCopy},
)
