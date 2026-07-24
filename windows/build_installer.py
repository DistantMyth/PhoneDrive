import os
import subprocess
import sys

def build():
    print("Building PhoneDrive installer...")
    
    # Ensure pyinstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        
    import customtkinter
    ctk_path = os.path.dirname(customtkinter.__file__)
    
    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name", "PhoneDrive",
        "--add-data", f"{ctk_path};customtkinter/",
        "main.py"
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    subprocess.check_call(cmd)
    print("Build complete. Check the 'dist' folder.")

if __name__ == "__main__":
    build()
