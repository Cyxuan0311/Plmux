import pathlib
import platform

if platform.system() == "Windows":
    pathlib.PosixPath = pathlib.WindowsPath
