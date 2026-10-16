import sys
import argparse
from phonedrive import __version__

def main():
    parser = argparse.ArgumentParser(description="PhoneDrive - Mount your phone as a Windows drive")
    parser.add_argument("--version", action="version", version=f"PhoneDrive {__version__}")
    parser.add_argument("--background", "-b", action="store_true",
                        help="Run in background without GUI (auto-mount saved devices)")
    parser.add_argument("--startup", action="store_true",
                        help="Register/unregister PhoneDrive to run on Windows startup")
    parser.add_argument("--no-startup", action="store_true",
                        help="Remove PhoneDrive from Windows startup")
    args = parser.parse_args()
    from phonedrive.logging_setup import configure_logging
    configure_logging()

    if args.startup:
        from phonedrive.autorun import add_to_startup
        add_to_startup()
        print("PhoneDrive added to Windows startup.")
        return

    if args.no_startup:
        from phonedrive.autorun import remove_from_startup
        remove_from_startup()
        print("PhoneDrive removed from Windows startup.")
        return

    from phonedrive.instance import SingleInstance
    instance = SingleInstance()
    if not instance.acquired:
        if not args.background:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, "PhoneDrive is already running. Open it from the system tray.", "PhoneDrive", 0x40)
        return

    if args.background:
        from phonedrive.background import run_background
        run_background()
    else:
        from phonedrive.app import main as app_main
        app_main()

if __name__ == "__main__":
    main()
