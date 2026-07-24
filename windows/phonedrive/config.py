import json
import os
import base64
from dataclasses import dataclass, asdict

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

    def _obfuscate(self, text: str) -> str:
        key = 0xAA
        return base64.b64encode(bytes([b ^ key for b in text.encode('utf-8')])).decode('utf-8')

    def _deobfuscate(self, obfuscated: str) -> str:
        try:
            key = 0xAA
            decoded = base64.b64decode(obfuscated)
            return bytes([b ^ key for b in decoded]).decode('utf-8')
        except Exception:
            return ""

    def encrypt_password(self, password: str) -> str:
        return self._obfuscate(password)

    def decrypt_password(self, password_encrypted: str) -> str:
        return self._deobfuscate(password_encrypted)

    def load(self):
        if not os.path.exists(self.config_path):
            return
        try:
            with open(self.config_path, 'r') as f:
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
        except Exception as e:
            print(f"Error loading config: {e}")

    def save(self):
        data = {
            'default_drive_letter': self.default_drive_letter,
            'auto_mount': self.auto_mount,
            'theme': self.theme,
            'window_geometry': self.window_geometry,
            'minimize_to_tray': self.minimize_to_tray,
            'saved_devices': [asdict(d) for d in self.saved_devices]
        }
        try:
            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")
