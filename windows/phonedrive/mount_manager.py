import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import ipaddress
import string
import subprocess
import threading


@dataclass(frozen=True)
class MountInfo:
    drive_letter: str
    remote_path: str
    status: str


class NetResource(ctypes.Structure):
    _fields_ = [("scope", wintypes.DWORD), ("type", wintypes.DWORD),
                ("display_type", wintypes.DWORD), ("usage", wintypes.DWORD),
                ("local_name", wintypes.LPWSTR), ("remote_name", wintypes.LPWSTR),
                ("comment", wintypes.LPWSTR), ("provider", wintypes.LPWSTR)]


def drive_name(value):
    drive = value.upper().removesuffix(":")
    if len(drive) != 1 or drive not in string.ascii_uppercase:
        raise ValueError("Choose a valid drive letter")
    return drive


class MountManager:
    def __init__(self):
        self._lock = threading.RLock()

    @staticmethod
    def remote_path(ip, port, username):
        ipaddress.IPv4Address(ip)
        if not 1 <= int(port) <= 65535 or not username or any(c in username for c in "\\/@!\r\n"):
            raise ValueError("Invalid SFTP address, port, or username")
        return f"\\\\sshfs\\{username}@{ip}!{port}"

    @staticmethod
    def same_remote(first, second):
        return first.rstrip("\\") == second.rstrip("\\")

    @staticmethod
    def _get_mapping(drive):
        function = ctypes.WinDLL("mpr", use_last_error=True).WNetGetConnectionW
        function.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        function.restype = wintypes.DWORD
        size = wintypes.DWORD(2048)
        buffer = ctypes.create_unicode_buffer(size.value)
        code = function(f"{drive}:", buffer, ctypes.byref(size))
        if code == 234:
            buffer = ctypes.create_unicode_buffer(size.value)
            code = function(f"{drive}:", buffer, ctypes.byref(size))
        if code in (2250, 1200):
            return None
        if code not in (0, 1201):
            raise ctypes.WinError(code)
        return MountInfo(drive, buffer.value, "OK" if code == 0 else "Disconnected")

    def get_mapping(self, drive):
        with self._lock:
            return self._get_mapping(drive_name(drive))

    @staticmethod
    def _connect(drive, remote, username, password):
        function = ctypes.WinDLL("mpr").WNetAddConnection2W
        function.argtypes = [ctypes.POINTER(NetResource), wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD]
        function.restype = wintypes.DWORD
        resource = NetResource(type=1, local_name=f"{drive}:", remote_name=remote)
        return function(ctypes.byref(resource), password, username, 0)

    def mount(self, ip, port, username, password, drive_letter):
        try:
            drive = drive_name(drive_letter)
            remote = self.remote_path(ip, port, username)
            if not password:
                return False, "Enter the phone's password."
            with self._lock:
                existing = self.get_mapping(drive)
                if existing:
                    if existing.status == "OK" and self.same_remote(existing.remote_path, remote):
                        return True, "Already mounted."
                    return False, "Drive is occupied; disconnect its existing mapping first."
                if drive not in self.get_available_drive_letters():
                    return False, "Drive letter is in use by another device."
                code = self._connect(drive, remote, username, password)
            return (True, "Mounted successfully.") if code == 0 else (False, ctypes.FormatError(code).strip())
        except (ValueError, OSError) as error:
            return False, str(error)

    @staticmethod
    def _disconnect(drive):
        function = ctypes.WinDLL("mpr").WNetCancelConnection2W
        function.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.BOOL]
        function.restype = wintypes.DWORD
        return function(f"{drive}:", 0, False)

    def unmount(self, drive_letter, unc_path=None):
        with self._lock:
            drive = drive_name(drive_letter)
            current = self.get_mapping(drive)
            if current is None:
                return True
            if not current.remote_path.lower().startswith("\\\\sshfs"):
                return False
            if unc_path and not self.same_remote(current.remote_path, unc_path):
                return False
            return self._disconnect(drive) in (0, 2250)

    def is_mounted(self, drive_letter, remote=None):
        info = self.get_mapping(drive_letter)
        return bool(info and info.status == "OK" and
                    (remote is None or self.same_remote(info.remote_path, remote)))

    def get_mounted_drives(self):
        return [info for drive in string.ascii_uppercase
                if (info := self.get_mapping(drive)) and info.remote_path.lower().startswith("\\\\sshfs")]

    @staticmethod
    def _logical_drives():
        return ctypes.WinDLL("kernel32").GetLogicalDrives()

    def get_available_drive_letters(self):
        bitmask = self._logical_drives()
        drives = [letter for i, letter in enumerate(string.ascii_uppercase) if not bitmask & (1 << i)]
        return [d for d in drives if d in "PQRSTUVWXYZ"] + [d for d in drives if d not in "PQRSTUVWXYZ"]

    def open_in_explorer(self, drive_letter):
        subprocess.Popen(["explorer.exe", f"{drive_name(drive_letter)}:\\"],
                         creationflags=subprocess.CREATE_NO_WINDOW)
