import json
import os
import logging
import tempfile
import threading
from dataclasses import dataclass, asdict
from . import credentials

@dataclass
class SavedDevice:
    name: str
    ip: str
    port: int
    username: str
    password_encrypted: str
    drive_letter: str

class Config:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self._lock = threading.RLock()
        self.appdata_dir = os.path.join(os.environ.get('APPDATA', ''), 'PhoneDrive')
        os.makedirs(self.appdata_dir, exist_ok=True)
        self.config_path = os.path.join(self.appdata_dir, 'config.json')

        # Defaults
        self.default_drive_letter = "P"
        self.auto_mount = False
        self.theme = "dark"
        self.saved_devices: list[SavedDevice] = []
        self.window_geometry = ""
        self.minimize_to_tray = True

        self.load()

    def encrypt_password(self, password: str) -> str:
        return credentials.protect(password)

    def decrypt_password(self, password_encrypted: str) -> str:
        return credentials.unprotect(password_encrypted)

    def load(self):
        if not os.path.exists(self.config_path):
            return
        try:
            with self._lock, open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.default_drive_letter = data.get('default_drive_letter', self.default_drive_letter)
                self.auto_mount = data.get('auto_mount', self.auto_mount)
                self.theme = data.get('theme', self.theme)
                self.window_geometry = data.get('window_geometry', self.window_geometry)
                self.minimize_to_tray = data.get('minimize_to_tray', self.minimize_to_tray)
                
                devices_data = data.get('saved_devices', [])
                self.saved_devices = []
                for d in devices_data:
                    self.saved_devices.append(SavedDevice(**d))
            if any(not d.password_encrypted.startswith(credentials.PREFIX) for d in self.saved_devices):
                self.save()
        except Exception:
            logging.getLogger(__name__).exception("Unable to load or migrate saved configuration")

    def save(self):
        with self._lock:
            self._save()

    def _save(self):
        devices = []
        for device in self.saved_devices:
            data = asdict(device)
            if not device.password_encrypted.startswith(credentials.PREFIX):
                data['password_encrypted'] = self.encrypt_password(self.decrypt_password(device.password_encrypted))
            devices.append(data)
        data = {
            'default_drive_letter': self.default_drive_letter,
            'auto_mount': self.auto_mount,
            'theme': self.theme,
            'window_geometry': self.window_geometry,
            'minimize_to_tray': self.minimize_to_tray,
            'saved_devices': devices
        }
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.appdata_dir,
                                             prefix='config-', suffix='.tmp', delete=False) as f:
                temporary = f.name
                json.dump(data, f, indent=4)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporary, self.config_path)
            for device, stored in zip(self.saved_devices, devices):
                device.password_encrypted = stored['password_encrypted']
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)
