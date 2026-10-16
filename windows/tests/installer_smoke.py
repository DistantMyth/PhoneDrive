"""Opt-in real installer lifecycle check, isolated from existing app settings.

Run with --installer <current.exe> --previous-installer <older-test.exe>.
The previous installer can be compiled with an older AppVersion from the same
payload to test the first installer release's upgrade/downgrade behavior.
"""
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import time
import winreg

KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{AD9693D4-F584-4A15-8E39-9242E3C657D2}_is1"


def installed_version():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY) as key:
            return winreg.QueryValueEx(key, "DisplayVersion")[0]
    except FileNotFoundError:
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installer", type=Path, required=True)
    parser.add_argument("--previous-installer", type=Path, required=True)
    parser.add_argument("--version", default="1.1.1")
    args = parser.parse_args()
    assert installed_version() is None, "Use a clean test account: an installed PhoneDrive must not be replaced by this test"
    config = Path(os.environ["APPDATA"]) / "PhoneDrive" / "config.json"
    original = hashlib.sha256(config.read_bytes()).digest() if config.exists() else None
    workspace = Path(__file__).resolve().parents[3]
    with tempfile.TemporaryDirectory(prefix="phonedrive-installer-test-", dir=workspace) as folder:
        root = Path(folder).resolve()
        assert root.is_relative_to(workspace)
        destination = root / "application"
        uninstaller = destination / "unins000.exe"

        def install(executable, label, choose_dir=False):
            command = [str(executable.resolve()), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
                       "/NOICONS", f"/LOG={root / (label + '.log')}"]
            if choose_dir:
                command += [f"/DIR={destination}"]
            return subprocess.run(command, timeout=120).returncode

        try:
            assert install(args.previous_installer, "initial", True) == 0
            assert installed_version() is not None
            print("PASS: initial install registers in Installed Apps", flush=True)
            assert install(args.installer, "upgrade") == 0
            assert installed_version() == args.version
            executable = destination / "PhoneDrive.exe"
            assert executable.is_file(), "Upgrade must retain the selected install directory"
            assert install(args.installer, "reinstall") == 0
            print("PASS: upgrade and reinstall retain the installation and version entry", flush=True)
            before = hashlib.sha256(executable.read_bytes()).digest()
            assert install(args.previous_installer, "downgrade") != 0
            assert installed_version() == args.version
            assert hashlib.sha256(executable.read_bytes()).digest() == before
            print("PASS: downgrade rejected without replacing files", flush=True)
            env = dict(os.environ, APPDATA=str(root / "test-settings"))
            subprocess.run([str(executable), "--version"], env=env, timeout=15, check=True)
            first = subprocess.Popen([str(executable), "--background"], env=env,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.OpenMutexW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
            kernel.OpenMutexW.restype = wintypes.HANDLE
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            try:
                for _ in range(100):
                    assert first.poll() is None, "Installed application exited unexpectedly"
                    handle = kernel.OpenMutexW(0x100000, False, "Local\\PhoneDrive.Desktop")
                    if handle:
                        kernel.CloseHandle(handle)
                        break
                    time.sleep(0.1)
                else:
                    raise AssertionError("Installed application did not acquire its instance mutex")
                second = subprocess.run([str(executable), "--background"], env=env, timeout=15)
                assert second.returncode == 0 and first.poll() is None
                print("PASS: installed application launches and duplicate process exits", flush=True)
            finally:
                if first.poll() is None:
                    first.terminate()
                    first.wait(timeout=15)
        finally:
            if uninstaller.exists():
                result = subprocess.run([str(uninstaller), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
                                         f"/LOG={root / 'uninstall.log'}"], timeout=120)
                assert result.returncode == 0
                for _ in range(100):
                    if installed_version() is None and not (destination / "PhoneDrive.exe").exists():
                        break
                    time.sleep(0.1)
                assert installed_version() is None
                assert not (destination / "PhoneDrive.exe").exists()
                # Inno's bootstrap can exit before its copied uninstaller closes the log.
                for _ in range(100):
                    if "Log closed." in (root / "uninstall.log").read_text(encoding="utf-8-sig"):
                        break
                    time.sleep(0.1)
                else:
                    raise AssertionError("Uninstaller did not finish writing its log")
                after = hashlib.sha256(config.read_bytes()).digest() if config.exists() else None
                assert after == original, "User settings changed during installer testing"
                print("PASS: uninstaller removes app/registration and preserves existing user settings", flush=True)


if __name__ == "__main__":
    main()
