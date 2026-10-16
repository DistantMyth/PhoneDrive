"""User-scoped Windows DPAPI storage, with migration from the v1 XOR format."""
import base64
import ctypes
from ctypes import wintypes

PREFIX = "dpapi:v1:"


class Blob(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]


def _crypt(data: bytes, protect: bool) -> bytes:
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    source = Blob(len(data), buffer)
    result = Blob()
    function = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                         ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(result)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(result.data, result.size)
    finally:
        kernel32.LocalFree(result.data)


def protect(password: str) -> str:
    if not password:
        raise ValueError("Password must not be empty")
    return PREFIX + base64.b64encode(_crypt(password.encode("utf-8"), True)).decode("ascii")


def unprotect(encoded: str) -> str:
    if encoded.startswith(PREFIX):
        raw = base64.b64decode(encoded[len(PREFIX):], validate=True)
        return _crypt(raw, False).decode("utf-8")
    raw = base64.b64decode(encoded, validate=True)
    password = bytes(b ^ 0xAA for b in raw).decode("utf-8")
    if not password:
        raise ValueError("Saved password is empty; enter it again")
    return password
