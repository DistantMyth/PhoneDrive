"""mDNS is a directory, not a heartbeat for an established SSH connection."""
import logging
import threading
import time
from dataclasses import dataclass
from typing import Callable
from zeroconf import IPVersion, ServiceBrowser, ServiceListener, Zeroconf

log = logging.getLogger(__name__)
SERVICE_TYPE = "_sftp-ssh._tcp.local."


@dataclass(frozen=True)
class DeviceInfo:
    name: str
    ip: str
    port: int
    hostname: str
    last_seen: float


class DeviceDiscovery(ServiceListener):
    def __init__(self):
        self.zeroconf = None
        self.browser = None
        self.devices: dict[str, DeviceInfo] = {}
        self.on_device_found: Callable[[DeviceInfo], None] | None = None
        self.on_device_lost: Callable[[str], None] | None = None
        self.scanning = False
        self._lock = threading.Lock()

    def start_scanning(self):
        if self.scanning:
            return
        self.zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
        self.scanning = True
        try:
            self.browser = ServiceBrowser(self.zeroconf, SERVICE_TYPE, self)
        except Exception:
            self.stop_scanning()
            raise

    def stop_scanning(self):
        self.scanning = False
        browser, zc = self.browser, self.zeroconf
        self.browser = self.zeroconf = None
        if browser:
            browser.cancel()
        if zc:
            zc.close()
        with self._lock:
            self.devices.clear()

    def remove_service(self, zc, type_, name):
        if not self.scanning or zc is not self.zeroconf:
            return
        friendly_name = name.removesuffix("." + type_)
        with self._lock:
            removed = self.devices.pop(friendly_name, None)
        if removed and self.on_device_lost:
            self.on_device_lost(friendly_name)

    def add_service(self, zc, type_, name):
        if not self.scanning or zc is not self.zeroconf:
            return
        try:
            info = zc.get_service_info(type_, name, timeout=2000)
            if not info:
                return
            addresses = info.parsed_addresses(IPVersion.V4Only)
            if not addresses or not 1 <= info.port <= 65535:
                return
            device = DeviceInfo(name.removesuffix("." + type_), addresses[0],
                                info.port, info.server or "", time.monotonic())
            with self._lock:
                if not self.scanning or zc is not self.zeroconf:
                    return
                self.devices[device.name] = device
            if self.on_device_found:
                self.on_device_found(device)
        except Exception:
            log.exception("Unable to resolve discovered device")

    def update_service(self, zc, type_, name):
        self.add_service(zc, type_, name)

    def manual_refresh(self):
        self.stop_scanning()
        self.start_scanning()
