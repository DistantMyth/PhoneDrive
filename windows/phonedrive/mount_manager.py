import subprocess
import string
import os
from dataclasses import dataclass

@dataclass
class MountInfo:
    drive_letter: str
    remote_path: str
    status: str

class MountManager:
    @staticmethod
    def _run_cmd(cmd: list[str]) -> tuple[bool, str]:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                return False, result.stderr.strip() or result.stdout.strip()
        except Exception as e:
            return False, str(e)

    def mount(self, ip: str, port: int, username: str, password: str, drive_letter: str) -> tuple[bool, str]:
        drive_letter = drive_letter.upper().replace(":", "")
        # Remove .r and \sdcard because the Android app already roots the SFTP server at /storage/emulated/0/
        remote_unc = f"\\\\sshfs\\{username}@{ip}!{port}"
        
        # 2. Mount drive and pass credentials directly
        # net use {drive}: {remote_unc} /user:{username} {password} /persistent:no
        mount_cmd = ["net", "use", f"{drive_letter}:", remote_unc, f"/user:{username}", password, "/persistent:no"]
        success, msg = self._run_cmd(mount_cmd)
        
        if success:
            return True, "Mounted successfully."
        else:
            return False, f"Mount failed: {msg}"

    def unmount(self, drive_letter: str, unc_path: str = None) -> bool:
        drive_letter = drive_letter.upper().replace(":", "")
        
        # unmount
        unmount_cmd = ["net", "use", f"{drive_letter}:", "/delete", "/y"]
        success, _ = self._run_cmd(unmount_cmd)
        
        # delete credentials if UNC is known (heuristics could be applied)
        if unc_path:
            # Expected UNC format: \\sshfs.r\username@ip!port\sdcard
            # The target for cmdkey is \\sshfs.r\username@ip!port
            try:
                parts = unc_path.split("\\")
                if len(parts) >= 4 and parts[2] == "sshfs.r":
                    target = f"\\{parts[2]}\\{parts[3]}"
                    self._run_cmd(["cmdkey", f"/delete:{target}"])
            except Exception:
                pass
                
        return success

    def is_mounted(self, drive_letter: str) -> bool:
        drive_letter = drive_letter.upper().replace(":", "")
        success, out = self._run_cmd(["net", "use"])
        if success:
            return f"{drive_letter}:" in out
        return False

    def get_mounted_drives(self) -> list[MountInfo]:
        mounts = []
        success, out = self._run_cmd(["net", "use"])
        if success:
            lines = out.split("\n")
            for line in lines:
                parts = line.split()
                if len(parts) >= 3 and parts[0] in ("OK", "Disconnected") and parts[1].endswith(":"):
                    status = parts[0]
                    drive = parts[1].replace(":", "")
                    remote = parts[2]
                    if remote.startswith("\\\\sshfs"):
                        mounts.append(MountInfo(drive_letter=drive, remote_path=remote, status=status))
        return mounts

    def get_available_drive_letters(self) -> list[str]:
        # Simple logical drives check
        import ctypes
        drives = []
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for i, letter in enumerate(string.ascii_uppercase):
            if not (bitmask & (1 << i)):
                drives.append(letter)
                
        # prefer P, Q, R...
        preferred = [d for d in drives if d in "PQRSTUVWXYZ"]
        others = [d for d in drives if d not in "PQRSTUVWXYZ"]
        return preferred + others

    def open_in_explorer(self, drive_letter: str):
        drive_letter = drive_letter.upper().replace(":", "")
        path = f"{drive_letter}:\\"
        subprocess.Popen(["explorer.exe", path], creationflags=subprocess.CREATE_NO_WINDOW)
