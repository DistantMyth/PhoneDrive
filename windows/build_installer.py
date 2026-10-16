"""Build the frozen application and its Inno Setup installer."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

from phonedrive import __version__

HERE = Path(__file__).resolve().parent


def find_compiler(explicit):
    candidates = [explicit, os.environ.get("ISCC"), shutil.which("ISCC.exe")]
    for base in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles")):
        if base:
            candidates.extend(str(p / "ISCC.exe") for p in Path(base).glob("Inno Setup *"))
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate).resolve())
    raise SystemExit("Install Inno Setup, then pass --iscc <path-to-ISCC.exe> or set ISCC.")


def write_version_info():
    version = tuple(int(n) for n in __version__.split(".")) + (0,)
    output = HERE / "build" / "version_info.txt"
    output.parent.mkdir(exist_ok=True)
    strings = {"CompanyName": "DistantMyth", "FileDescription": "PhoneDrive",
               "FileVersion": __version__, "ProductName": "PhoneDrive",
               "ProductVersion": __version__, "OriginalFilename": "PhoneDrive.exe"}
    entries = ",".join(f"StringStruct({k!r}, {v!r})" for k, v in strings.items())
    output.write_text(
        f"VSVersionInfo(ffi=FixedFileInfo(filevers={version!r}, prodvers={version!r}, "
        "mask=0x3f, flags=0, OS=0x40004, fileType=1, subtype=0, date=(0,0)), "
        f"kids=[StringFileInfo([StringTable('040904B0', [{entries}])]), "
        "VarFileInfo([VarStruct('Translation', [1033,1200])])])", encoding="utf-8")
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iscc", help="Path to Inno Setup's ISCC.exe")
    args = parser.parse_args()
    compiler = find_compiler(args.iscc)
    import customtkinter
    subprocess.run([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir",
        "--windowed", "--name", "PhoneDrive", "--version-file", str(write_version_info()),
        "--add-data", f"{Path(customtkinter.__file__).parent};customtkinter/", "main.py"
    ], cwd=HERE, check=True)
    subprocess.run([compiler, f"/DAppVersion={__version__}", str(HERE / "installer.iss")],
                   cwd=HERE, check=True)
    print(f"Installer: {HERE / 'dist' / ('PhoneDrive-Setup-' + __version__ + '.exe')}")


if __name__ == "__main__":
    main()
