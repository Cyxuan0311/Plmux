import sys


def _patch_posix():
    import pathlib

    if hasattr(pathlib, "PosixPath"):
        pathlib.PosixPath = pathlib.WindowsPath
    if hasattr(pathlib, "PurePosixPath"):
        pathlib.PurePosixPath = pathlib.PureWindowsPath

    for mod in list(sys.modules.values()):
        for name in ("PosixPath", "PurePosixPath"):
            if name in mod.__dict__:
                replacement = getattr(pathlib, name.replace("Posix", "Windows"), None)
                if replacement is not None:
                    mod.__dict__[name] = replacement


def pytest_configure(config):
    if sys.platform == "win32":
        _patch_posix()