import sys
import os
import winreg

APP_NAME = "PhoneDrive"
REG_PATH = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"

def get_exe_path() -> str:
    """Get the path to the current executable or script."""
    if getattr(sys, 'frozen', False):
        # Running as compiled exe (PyInstaller)
        return f'"{sys.executable}" --background'
    else:
        # Running as script
        script = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'main.py'))
        python_exe = sys.executable
        if python_exe.lower().endswith("python.exe"):
            pythonw = os.path.join(os.path.dirname(python_exe), "pythonw.exe")
            if os.path.exists(pythonw):
                python_exe = pythonw
        return f'"{python_exe}" "{script}" --background'

def add_to_startup(background: bool = True) -> bool:
    """Add PhoneDrive to Windows startup."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE)
        exe_path = get_exe_path()
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"Failed to add to startup: {e}")
        return False

def remove_from_startup() -> bool:
    """Remove PhoneDrive from Windows startup."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return True  # Already not in startup
    except Exception as e:
        print(f"Failed to remove from startup: {e}")
        return False

def is_in_startup() -> bool:
    """Check if PhoneDrive is in Windows startup."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False