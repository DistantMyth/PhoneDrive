# PhoneDrive Windows

A modern Windows desktop application to discover and mount Android phones running the PhoneDrive SFTP server on the local network as Windows drive letters.

## Features
- Discovers Android devices running PhoneDrive via mDNS (zeroconf).
- Mounts SFTP server as a local drive using WinFsp and SSHFS-Win.
- Modern, dark-mode GUI built with CustomTkinter.
- Tray icon for quick access.

## Prerequisites
- Python 3.10+
- [WinFsp](https://winfsp.dev/)
- [SSHFS-Win](https://github.com/winfsp/sshfs-win)

## Installation
```bash
pip install -r requirements.txt
python main.py
```

## Build
To build a standalone executable:
```bash
python build_installer.py
```

## Credits
Built with CustomTkinter, SSHFS-Win, WinFsp, python-zeroconf.
