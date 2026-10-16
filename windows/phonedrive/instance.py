"""One desktop process per Windows login, shared with the installer."""
import ctypes
from ctypes import wintypes

MUTEX_NAME = "Local\\PhoneDrive.Desktop"


class SingleInstance:
    def __init__(self):
        self._kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self._kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        self._kernel.CreateMutexW.restype = wintypes.HANDLE
        self._kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self._kernel.CloseHandle.restype = wintypes.BOOL
        self.handle = self._kernel.CreateMutexW(None, False, MUTEX_NAME)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        self.acquired = ctypes.get_last_error() != 183  # ERROR_ALREADY_EXISTS

    def __del__(self):
        if getattr(self, "handle", None):
            self._kernel.CloseHandle(self.handle)
            self.handle = None
