import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="PhoneDrive - Mount your phone as a Windows drive")
    parser.add_argument("--background", "-b", action="store_true",
                        help="Run in background without GUI (auto-mount saved devices)")
    parser.add_argument("--startup", action="store_true",
                        help="Register/unregister PhoneDrive to run on Windows startup")
    parser.add_argument("--no-startup", action="store_true",
                        help="Remove PhoneDrive from Windows startup")
    args = parser.parse_args()

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

    if args.background:
        from phonedrive.background import run_background
        run_background()
    else:
        from phonedrive.app import main as app_main
        app_main()

if __name__ == "__main__":
    main()