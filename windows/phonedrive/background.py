import logging
import signal
import socket
import threading
import time
from dataclasses import dataclass
from .discovery import DeviceDiscovery, DeviceInfo
from .mount_manager import MountManager
from .config import Config, SavedDevice
from .prerequisites import get_status

log = logging.getLogger("PhoneDrive")


def ssh_reachable(ip, port):
    """Bounded liveness probe, not authentication or proof of mount health."""
    try:
        with socket.create_connection((ip, port), timeout=2) as connection:
            connection.settimeout(2)
            return connection.recv(255).startswith(b"SSH-")
    except OSError:
        return False


@dataclass
class Recovery:
    remote: str = ""
    failures: int = 0
    retry_at: float = 0
    outage: bool = False


class BackgroundService:
    def __init__(self, config=None, mount_manager=None, discovery=None, probe=ssh_reachable):
        self.config = config if config is not None else Config()
        self.mount_manager = mount_manager if mount_manager is not None else MountManager()
        self.discovery = discovery if discovery is not None else DeviceDiscovery()
        self.probe = probe
        self.known_devices: dict[str, DeviceInfo] = {}
        self.manual_devices: dict[str, SavedDevice] = {}
        self.suppressed: set[str] = set()
        self.recovery: dict[str, Recovery] = {}
        self.mounted_devices: dict[str, str] = {}
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread = None

    def on_device_found(self, device):
        with self._lock:
            previous = self.known_devices.get(device.name)
            self.known_devices[device.name] = device
            if previous and (previous.ip, previous.port) != (device.ip, device.port):
                self.recovery.setdefault(device.name, Recovery()).retry_at = 0

    def on_device_lost(self, name):
        # Discovery removal never owns the lifetime of an established mount.
        log.info("Advertisement unavailable for %s; retaining connection", name)

    def track(self, saved):
        with self._lock:
            self.manual_devices[saved.name] = saved
            self.suppressed.discard(saved.name)
            self.recovery[saved.name] = Recovery(
                remote=self.mount_manager.remote_path(saved.ip, saved.port, saved.username))
            self.mounted_devices[saved.name] = saved.drive_letter

    def untrack_drive(self, drive):
        with self._lock:
            for saved in list(self.config.saved_devices) + list(self.manual_devices.values()):
                if saved.drive_letter.upper() == drive.upper():
                    self.suppressed.add(saved.name)
                    self.manual_devices.pop(saved.name, None)
                    self.recovery.pop(saved.name, None)
                    self.mounted_devices.pop(saved.name, None)

    def _retry(self, state, now):
        state.failures += 1
        state.retry_at = now + min(60, 5 * 2 ** min(state.failures - 1, 4))

    def reconcile(self, now=None):
        now = time.monotonic() if now is None else now
        # Serialize user unmount requests with recovery so a stale snapshot
        # cannot immediately re-create a mapping explicitly removed in the GUI.
        with self._lock:
            desired = {d.name: d for d in self.config.saved_devices} if self.config.auto_mount else {}
            desired.update(self.manual_devices)
            for name, saved in desired.items():
                if name in self.suppressed or self._stop.is_set():
                    continue
                state = self.recovery.setdefault(name, Recovery())
                if now < state.retry_at:
                    continue
                device = self.known_devices.get(name) or DeviceInfo(name, saved.ip, saved.port, "", now)
                try:
                    self._reconcile_device(device, saved, state, now)
                except Exception:
                    log.exception("Recovery failed for %s", name)
                    self._retry(state, now)

    def _reconcile_device(self, device, saved, state, now):
        mm = self.mount_manager
        expected = mm.remote_path(device.ip, device.port, saved.username)
        saved_remote = mm.remote_path(saved.ip, saved.port, saved.username)
        mapping = mm.get_mapping(saved.drive_letter)
        if mapping and not any(mm.same_remote(mapping.remote_path, remote)
                               for remote in (expected, saved_remote, state.remote) if remote):
            log.warning("Drive %s: belongs to another connection; leaving it untouched", saved.drive_letter)
            self._retry(state, now)
            return
        if not self.probe(device.ip, device.port):
            # Multiple probes are required before considering recovery. No
            # mapping is torn down while the endpoint is unavailable.
            self._retry(state, now)
            state.outage = state.outage or state.failures >= 3
            return
        if mapping and mapping.status == "OK" and mm.same_remote(mapping.remote_path, expected) and not state.outage:
            state.remote = expected
            state.failures = 0
            state.retry_at = now + 15
            self.mounted_devices[device.name] = saved.drive_letter
            return
        if mapping:
            # WNetCancelConnection2(force=False) refuses to close busy files.
            # Keep ownership and retry if the mapping cannot yet be removed.
            if not mm.unmount(saved.drive_letter, mapping.remote_path):
                self._retry(state, now)
                return
        password = self.config.decrypt_password(saved.password_encrypted)
        success, message = mm.mount(device.ip, device.port, saved.username, password, saved.drive_letter)
        if not success:
            log.warning("Mount failed for %s: %s", device.name, message)
            self._retry(state, now)
            return
        state.remote = expected
        state.failures = 0
        state.outage = False
        state.retry_at = now + 15
        self.mounted_devices[device.name] = saved.drive_letter
        # Keep a working endpoint available after a desktop restart even if
        # multicast discovery temporarily remains unavailable.
        if (saved.ip, saved.port) != (device.ip, device.port):
            saved.ip, saved.port = device.ip, device.port
            self.config.save()
        log.info("Connected %s on %s:", device.name, saved.drive_letter)

    def start_worker(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="PhoneDrive recovery", daemon=True)
        self._thread.start()

    def _loop(self):
        while not self._stop.is_set():
            try:
                self.reconcile()
            except Exception:
                log.exception("Connection monitor failed")
            self._stop.wait(5)

    def stop_worker(self):
        self._stop.set()

    def run(self):
        status = get_status()
        if not status.winfsp_installed or not status.sshfs_installed:
            raise RuntimeError("Install WinFsp and SSHFS-Win before starting PhoneDrive")
        self.discovery.on_device_found = self.on_device_found
        self.discovery.on_device_lost = self.on_device_lost
        self.discovery.start_scanning()
        self.start_worker()
        def shutdown(*_):
            self._stop.set()
        signal.signal(signal.SIGINT, shutdown)
        signal.signal(signal.SIGTERM, shutdown)
        try:
            while not self._stop.wait(1):
                pass
        except KeyboardInterrupt:
            pass
        finally:
            self.stop_worker()
            self.discovery.stop_scanning()
            # App shutdown, like discovery loss, must not abort open files.


def run_background():
    BackgroundService().run()
