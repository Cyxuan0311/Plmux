import sys
import os
from setuptools import Extension, setup

if sys.platform == 'win32':
    compile_args = ['/O2', '/GL']
    link_args = ['/LTCG']
    library_dirs = [os.path.join(sys.base_prefix, 'libs')]
else:
    compile_args = ['-O3', '-march=native', '-flto']
    link_args = ['-flto', '-lpthread']
    library_dirs = []

_fastscren_ext = Extension(
    "plmux.terminal._c_extension._fastscreen",
    sources=[
        "plmux/terminal/_c_extension/_fastscreen_module.c",
        "plmux/terminal/_c_extension/_fastscreen_screen.c",
        "plmux/terminal/_c_extension/_fastscreen_parser.c",
        "plmux/terminal/_c_extension/_fastscreen_debug.c",
        "plmux/terminal/_c_extension/_fastscreen_color.c",
        "plmux/terminal/_c_extension/_fastscreen_render.c",
        "plmux/terminal/_c_extension/_fastscreen_ansi.c",
    ],
    depends=[
        "plmux/terminal/_c_extension/_fastscreen_types.h",
        "plmux/terminal/_c_extension/_fastscreen_debug.h",
        "plmux/terminal/_c_extension/_fastscreen_color.h",
        "plmux/terminal/_c_extension/_fastscreen_render.h",
        "plmux/terminal/_c_extension/_fastscreen_ansi.h",
    ],
    extra_compile_args=compile_args,
    extra_link_args=link_args,
    library_dirs=library_dirs,
)

_ws_kernel_ext = Extension(
    "plmux.web._c_extension._ws_kernel",
    sources=[
        "plmux/web/_c_extension/_ws_kernel_module.c",
        "plmux/web/_c_extension/_ws_kernel_frame.c",
    ],
    depends=[
        "plmux/web/_c_extension/_ws_kernel.h",
    ],
    extra_compile_args=compile_args,
    extra_link_args=link_args,
    library_dirs=library_dirs,
)

setup(
    ext_modules=[_fastscren_ext, _ws_kernel_ext],
)
