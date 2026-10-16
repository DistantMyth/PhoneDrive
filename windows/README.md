# PhoneDrive Windows

A modern Windows desktop application to discover and mount Android phones running the PhoneDrive SFTP server on the local network as Windows drive letters.

## Features
- Discovers Android devices running PhoneDrive via mDNS (zeroconf).
- Mounts SFTP server as a local drive using WinFsp and SSHFS-Win.
- Modern, dark-mode GUI built with CustomTkinter.
- Tray icon for quick access.

## Prerequisites
- [WinFsp](https://winfsp.dev/)
- [SSHFS-Win](https://github.com/winfsp/sshfs-win)

## Installation
Download `PhoneDrive-Setup-<version>.exe` from [Releases](https://github.com/DistantMyth/PhoneDrive/releases/latest) and run it. Python is bundled. The installer adds PhoneDrive to the Start menu and Windows Installed Apps, and offers a desktop shortcut.

Future installers update the same installation and retain your saved devices and settings in `%APPDATA%\PhoneDrive`. Older installers cannot overwrite a newer installed version. Uninstall through Windows Installed Apps; saved settings are retained for a later reinstall.

If switching from the old ZIP build, exit its tray icon first, install the new version, then use the Start menu shortcut. If the portable copy was configured to start with Windows, disable that option in the old copy and enable it again in the installed copy.

WinFsp and SSHFS-Win remain required. PhoneDrive offers to install missing drivers when first launched; those driver installers may request administrator permission.

For development with Python 3.10+:
```bash
pip install -r requirements.txt
python main.py
```

## Build
Install [Inno Setup](https://jrsoftware.org/isinfo.php), then build with an isolated Python environment:
```bash
python -m pip install -r requirements-build.txt
python build_installer.py
```

If ISCC is not on PATH, pass `--iscc "C:\path\to\ISCC.exe"` or set `ISCC`. The script works from any working directory and uses the active Python environment. The output is `windows/dist/PhoneDrive-Setup-<version>.exe`. Version information comes from `phonedrive/__init__.py`; keep the installer AppId stable across releases.

## Credits
Built with CustomTkinter, SSHFS-Win, WinFsp, python-zeroconf.
