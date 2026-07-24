import threading
import time
import socket
from dataclasses import dataclass
from typing import Callable
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf

@dataclass
class DeviceInfo:
    name: str
    ip: str
    port: int
    hostname: str
    last_seen: float

class DeviceDiscovery(ServiceListener):
    def __init__(self):
        self.zeroconf: Zeroconf | None = None
        self.browser: ServiceBrowser | None = None
        self.devices: dict[str, DeviceInfo] = {}
        
        self.on_device_found: Callable[[DeviceInfo], None] | None = None
        self.on_device_lost: Callable[[str], None] | None = None
        
        self.scanning = False
        self._lock = threading.Lock()
        self._monitor_thread = None

    def start_scanning(self):
        if self.scanning:
            return
            
        self.scanning = True
        self.zeroconf = Zeroconf()
        self.browser = ServiceBrowser(self.zeroconf, "_sftp-ssh._tcp.local.", self)
        
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop_scanning(self):
        self.scanning = False
        if self.zeroconf:
            self.zeroconf.close()
            self.zeroconf = None
        if self.browser:
            self.browser.cancel()
            self.browser = None
        with self._lock:
            self.devices.clear()

    def _monitor_loop(self):
        while self.scanning:
            current_time = time.time()
            to_remove = []
            with self._lock:
                for name, info in self.devices.items():
                    if current_time - info.last_seen > 60:
                        to_remove.append(name)
                        
                for name in to_remove:
                    del self.devices[name]
                    
            for name in to_remove:
                if self.on_device_lost:
                    self.on_device_lost(name)
                    
            time.sleep(5)

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        friendly_name = name.replace("." + type_, "")
        with self._lock:
            if friendly_name in self.devices:
                del self.devices[friendly_name]
        if self.on_device_lost:
            self.on_device_lost(friendly_name)

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        if not info:
            return
            
        friendly_name = name.replace("." + type_, "")
        
        addresses = [socket.inet_ntoa(addr) for addr in info.addresses]
        if not addresses:
            return
            
        ip = addresses[0]
        port = info.port
        hostname = info.server
        
        device = DeviceInfo(
            name=friendly_name,
            ip=ip,
            port=port,
            hostname=hostname,
            last_seen=time.time()
        )
        
        with self._lock:
            self.devices[friendly_name] = device
            
        if self.on_device_found:
            self.on_device_found(device)

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        # Same as add
        self.add_service(zc, type_, name)

    def manual_refresh(self):
        self.stop_scanning()
        time.sleep(0.5)
        self.start_scanning()
