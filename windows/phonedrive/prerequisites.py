import os
import subprocess
import winreg
from dataclasses import dataclass

@dataclass
class PrereqStatus:
    winfsp_installed: bool
    sshfs_installed: bool

def check_winfsp() -> bool:
    try:
        # Check standard path
        if os.path.exists(r"C:\Program Files (x86)\WinFsp"):
            return True
        if os.path.exists(r"C:\Program Files\WinFsp"):
            return True
            
        # Check registry
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WinFsp")
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            pass
            
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\WinFsp")
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            pass
            
    except Exception:
        pass
    return False

def check_sshfs_win() -> bool:
    return os.path.exists(r"C:\Program Files\SSHFS-Win\bin\sshfs.exe")

def get_status() -> PrereqStatus:
    return PrereqStatus(
        winfsp_installed=check_winfsp(),
        sshfs_installed=check_sshfs_win()
    )

def install_winfsp():
    subprocess.Popen(
        ["winget", "install", "-e", "--id", "WinFsp.WinFsp", "--accept-package-agreements", "--accept-source-agreements"],
        creationflags=subprocess.CREATE_NEW_CONSOLE
    ).wait()

def install_sshfs_win():
    subprocess.Popen(
        ["winget", "install", "-e", "--id", "SSHFS-Win.SSHFS-Win", "--accept-package-agreements", "--accept-source-agreements"],
        creationflags=subprocess.CREATE_NEW_CONSOLE
    ).wait()
