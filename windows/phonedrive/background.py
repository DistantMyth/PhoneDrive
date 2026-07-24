import time
import signal
import sys
import logging
from .discovery import DeviceDiscovery, DeviceInfo
from .mount_manager import MountManager
from .config import Config
from .prerequisites import get_status

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [PhoneDrive] %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger("PhoneDrive")

class BackgroundService:
    def __init__(self):
        self.config = Config()
        self.mount_manager = MountManager()
        self.discovery = DeviceDiscovery()
        self.running = True
        self.mounted_devices: dict[str, str] = {}  # device_name -> drive_letter

    def on_device_found(self, device: DeviceInfo):
        log.info(f"Discovered device: {device.name} ({device.ip}:{device.port})")
        
        # Check if this device is saved and should be auto-mounted
        for saved in self.config.saved_devices:
            if saved.name == device.name or saved.ip == device.ip:
                if device.name not in self.mounted_devices:
                    self._auto_mount(device, saved)
                break
        else:
            # If auto_mount is enabled and we have no saved config, try with defaults
            if self.config.auto_mount and device.name not in self.mounted_devices:
                log.info(f"Device {device.name} not in saved list, skipping auto-mount")

    def on_device_lost(self, name: str):
        log.info(f"Device lost: {name}")
        if name in self.mounted_devices:
            drive = self.mounted_devices[name]
            log.info(f"Auto-unmounting {drive}: (device {name} went offline)")
            self.mount_manager.unmount(drive)
            del self.mounted_devices[name]

    def _auto_mount(self, device: DeviceInfo, saved):
        password = self.config.decrypt_password(saved.password_encrypted)
        drive = saved.drive_letter
        
        if self.mount_manager.is_mounted(drive):
            log.info(f"Drive {drive}: already mounted, skipping")
            return
        
        log.info(f"Auto-mounting {device.name} ({device.ip}:{device.port}) to {drive}:")
        success, msg = self.mount_manager.mount(
            device.ip, device.port, saved.username, password, drive
        )
        if success:
            log.info(f"Successfully mounted {device.name} to {drive}:")
            self.mounted_devices[device.name] = drive
        else:
            log.error(f"Failed to mount {device.name}: {msg}")

    def run(self):
        log.info("PhoneDrive background service starting...")
        
        # Check prerequisites
        status = get_status()
        if not status.winfsp_installed or not status.sshfs_installed:
            log.error("Missing prerequisites (WinFsp/SSHFS-Win). Run PhoneDrive GUI to install.")
            sys.exit(1)
        
        # Setup discovery callbacks
        self.discovery.on_device_found = self.on_device_found
        self.discovery.on_device_lost = self.on_device_lost
        self.discovery.start_scanning()
        
        log.info("Scanning for devices on local network...")
        log.info(f"Saved devices: {[d.name for d in self.config.saved_devices]}")
        
        # Setup signal handlers for clean shutdown
        def shutdown(signum, frame):
            log.info("Shutting down...")
            self.running = False
        
        signal.signal(signal.SIGINT, shutdown)
        signal.signal(signal.SIGTERM, shutdown)
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            log.info("Cleaning up...")
            # Unmount all
            for name, drive in list(self.mounted_devices.items()):
                log.info(f"Unmounting {drive}: ({name})")
                self.mount_manager.unmount(drive)
            self.discovery.stop_scanning()
            log.info("PhoneDrive background service stopped.")

def run_background():
    service = BackgroundService()
    service.run()