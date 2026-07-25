import customtkinter as ctk
import threading
import time
from typing import Dict, Any
from .discovery import DeviceDiscovery, DeviceInfo
from .mount_manager import MountManager
from .config import Config

class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent, config, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.title("Settings")
        self.geometry("400x350")
        self.resizable(False, False)
        self.config = config
        self.parent = parent
        
        self.grab_set()
        
        self.grid_columnconfigure(0, weight=1)
        
        # Drive Letter
        self.drive_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.drive_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        self.drive_label = ctk.CTkLabel(self.drive_frame, text="Default Drive Letter:")
        self.drive_label.pack(side="left", padx=10)
        self.drive_var = ctk.StringVar(value=self.config.default_drive_letter)
        mm = MountManager()
        letters = mm.get_available_drive_letters()
        if self.config.default_drive_letter not in letters:
            letters.insert(0, self.config.default_drive_letter)
        self.drive_combo = ctk.CTkComboBox(self.drive_frame, values=letters, variable=self.drive_var, width=80)
        self.drive_combo.pack(side="right", padx=10)
        
        # Auto Mount
        self.auto_mount_var = ctk.BooleanVar(value=self.config.auto_mount)
        self.auto_mount_switch = ctk.CTkSwitch(self, text="Auto-mount known devices", variable=self.auto_mount_var)
        self.auto_mount_switch.grid(row=1, column=0, padx=30, pady=10, sticky="w")
        
        # Minimize to Tray
        self.tray_var = ctk.BooleanVar(value=self.config.minimize_to_tray)
        self.tray_switch = ctk.CTkSwitch(self, text="Minimize to tray on close", variable=self.tray_var)
        self.tray_switch.grid(row=2, column=0, padx=30, pady=10, sticky="w")
        
        # Save Button
        self.save_btn = ctk.CTkButton(self, text="Save", command=self.save_settings)
        self.save_btn.grid(row=3, column=0, padx=20, pady=20, sticky="ew")
        
    def save_settings(self):
        self.config.default_drive_letter = self.drive_var.get()
        self.config.auto_mount = self.auto_mount_var.get()
        self.config.minimize_to_tray = self.tray_var.get()
        self.config.save()
        self.destroy()

class ManualConnectDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_connect, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.title("Manual Connect")
        self.geometry("400x450")
        self.resizable(False, False)
        self.on_connect = on_connect
        
        self.grab_set()
        self.grid_columnconfigure(1, weight=1)
        
        # Fields
        ctk.CTkLabel(self, text="IP Address:").grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        self.ip_entry = ctk.CTkEntry(self)
        self.ip_entry.grid(row=0, column=1, padx=20, pady=(20, 5), sticky="ew")
        
        ctk.CTkLabel(self, text="Port:").grid(row=1, column=0, padx=20, pady=5, sticky="w")
        self.port_entry = ctk.CTkEntry(self)
        self.port_entry.insert(0, "2222")
        self.port_entry.grid(row=1, column=1, padx=20, pady=5, sticky="ew")
        
        ctk.CTkLabel(self, text="Username:").grid(row=2, column=0, padx=20, pady=5, sticky="w")
        self.user_entry = ctk.CTkEntry(self)
        self.user_entry.insert(0, "phone")
        self.user_entry.grid(row=2, column=1, padx=20, pady=5, sticky="ew")
        
        ctk.CTkLabel(self, text="Password:").grid(row=3, column=0, padx=20, pady=5, sticky="w")
        self.pass_entry = ctk.CTkEntry(self, show="*")
        self.pass_entry.grid(row=3, column=1, padx=20, pady=5, sticky="ew")
        
        ctk.CTkLabel(self, text="Drive Letter:").grid(row=4, column=0, padx=20, pady=5, sticky="w")
        mm = MountManager()
        self.drive_var = ctk.StringVar(value=Config().default_drive_letter)
        self.drive_combo = ctk.CTkComboBox(self, values=mm.get_available_drive_letters(), variable=self.drive_var)
        self.drive_combo.grid(row=4, column=1, padx=20, pady=5, sticky="ew")
        
        self.connect_btn = ctk.CTkButton(self, text="Connect", command=self.connect)
        self.connect_btn.grid(row=5, column=0, columnspan=2, padx=20, pady=20, sticky="ew")
        
    def connect(self):
        ip = self.ip_entry.get()
        port = self.port_entry.get()
        user = self.user_entry.get()
        password = self.pass_entry.get()
        drive = self.drive_var.get()
        
        if not ip or not port or not user or not drive:
            return
            
        try:
            port = int(port)
        except ValueError:
            return
            
        self.on_connect(ip, port, user, password, drive)
        self.destroy()

class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.config = Config()
        self.mount_manager = MountManager()
        self.discovery = DeviceDiscovery()
        
        self.title("PhoneDrive")
        self.geometry("900x650")
        if self.config.window_geometry:
            try:
                self.geometry(self.config.window_geometry)
            except Exception:
                pass
                
        ctk.set_appearance_mode(self.config.theme)
        
        # Theme colors
        self.bg_color = "#1a1a2e"
        self.accent_color = "#4361ee"
        self.success_color = "#06d6a0"
        self.error_color = "#ef476f"
        
        # Grid layout
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=6)
        self.grid_columnconfigure(1, weight=4)
        
        self.build_ui()
        
        # Setup Discovery Callbacks
        self.discovery.on_device_found = self.on_device_found
        self.discovery.on_device_lost = self.on_device_lost
        
        self.devices = {}
        self.selected_device = None
        
        # Start scanning
        self.discovery.start_scanning()
        self.update_mounts_loop()
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def build_ui(self):
        # A. Header Bar
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=15)
        
        self.title_label = ctk.CTkLabel(self.header_frame, text="📱 PhoneDrive", font=("Segoe UI Semibold", 24))
        self.title_label.pack(side="left", padx=10)
        
        self.subtitle_label = ctk.CTkLabel(self.header_frame, text="Your phone, in your file manager", font=("Segoe UI", 14), text_color="gray")
        self.subtitle_label.pack(side="left", padx=10, pady=(6,0))
        
        self.settings_btn = ctk.CTkButton(self.header_frame, text="⚙️", width=40, font=("Segoe UI", 16), fg_color="transparent", border_width=1, command=self.open_settings)
        self.settings_btn.pack(side="right", padx=5)
        
        self.theme_btn = ctk.CTkButton(self.header_frame, text="🌓", width=40, font=("Segoe UI", 16), fg_color="transparent", border_width=1, command=self.toggle_theme)
        self.theme_btn.pack(side="right", padx=5)
        
        # B. Device Discovery Panel
        self.left_panel = ctk.CTkFrame(self, fg_color=("gray90", "gray13"), corner_radius=15)
        self.left_panel.grid(row=1, column=0, sticky="nsew", padx=(20, 10), pady=10)
        
        self.left_header = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.left_header.pack(fill="x", padx=15, pady=15)
        
        ctk.CTkLabel(self.left_header, text="Devices on Network", font=("Segoe UI Semibold", 16)).pack(side="left")
        
        self.scan_indicator = ctk.CTkLabel(self.left_header, text="Scanning...", text_color=self.accent_color, font=("Segoe UI", 12))
        self.scan_indicator.pack(side="left", padx=10)
        
        self.refresh_btn = ctk.CTkButton(self.left_header, text="Refresh", width=80, height=28, command=self.refresh_scan)
        self.refresh_btn.pack(side="right")
        
        self.devices_scroll = ctk.CTkScrollableFrame(self.left_panel, fg_color="transparent")
        self.devices_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        self.manual_btn = ctk.CTkButton(self.left_panel, text="Manual Connect", fg_color="transparent", border_width=1, command=self.open_manual_connect)
        self.manual_btn.pack(fill="x", padx=20, pady=15)
        
        # C. Connection/Mount Panel
        self.right_panel = ctk.CTkFrame(self, fg_color=("gray85", "gray10"), corner_radius=15)
        self.right_panel.grid(row=1, column=1, sticky="nsew", padx=(10, 20), pady=10)
        
        ctk.CTkLabel(self.right_panel, text="Mount Settings", font=("Segoe UI Semibold", 16)).pack(pady=20)
        
        self.form_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.form_frame.pack(fill="both", expand=True, padx=20)
        
        self.ip_var = ctk.StringVar()
        self.port_var = ctk.StringVar(value="2222")
        self.user_var = ctk.StringVar(value="phone")
        self.pass_var = ctk.StringVar()
        self.drive_var = ctk.StringVar(value=self.config.default_drive_letter)
        
        self.add_form_field("IP Address:", self.ip_var)
        self.add_form_field("Port:", self.port_var)
        self.add_form_field("Username:", self.user_var)
        
        pass_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        pass_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(pass_frame, text="Password:", width=80, anchor="w").pack(side="left")
        self.pass_entry = ctk.CTkEntry(pass_frame, textvariable=self.pass_var, show="*")
        self.pass_entry.pack(side="left", fill="x", expand=True, padx=(10, 5))
        self.show_pass_btn = ctk.CTkButton(pass_frame, text="👁", width=30, fg_color="transparent", command=self.toggle_pass_visibility)
        self.show_pass_btn.pack(side="right")
        
        drive_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        drive_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(drive_frame, text="Drive:", width=80, anchor="w").pack(side="left")
        self.drive_combo = ctk.CTkComboBox(drive_frame, values=self.mount_manager.get_available_drive_letters(), variable=self.drive_var)
        self.drive_combo.pack(side="left", fill="x", expand=True, padx=10)
        
        self.mount_btn = ctk.CTkButton(self.right_panel, text="Mount Drive", height=45, font=("Segoe UI Semibold", 14), 
                                      fg_color=self.accent_color, hover_color="#304ffe", command=self.do_mount)
        self.mount_btn.pack(fill="x", padx=30, pady=10)
        
        self.unmount_btn = ctk.CTkButton(self.right_panel, text="Unmount", height=45, font=("Segoe UI Semibold", 14),
                                        fg_color=self.error_color, hover_color="#d81159", command=self.do_unmount)
        self.unmount_btn.pack(fill="x", padx=30, pady=10)
        self.unmount_btn.pack_forget() # Hide initially
        
        # D. Active Mounts Panel
        self.bottom_panel = ctk.CTkFrame(self, height=150, corner_radius=0, fg_color="transparent")
        self.bottom_panel.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=20, pady=(10, 0))
        self.bottom_panel.grid_propagate(False)
        
        bot_header = ctk.CTkFrame(self.bottom_panel, fg_color="transparent")
        bot_header.pack(fill="x")
        ctk.CTkLabel(bot_header, text="Mounted Drives", font=("Segoe UI Semibold", 14)).pack(side="left")
        ctk.CTkButton(bot_header, text="Eject All", width=80, height=24, fg_color="transparent", border_width=1, command=self.unmount_all).pack(side="right")
        
        self.mounts_scroll = ctk.CTkScrollableFrame(self.bottom_panel, fg_color=("gray90", "gray13"), corner_radius=10)
        self.mounts_scroll.pack(fill="both", expand=True, pady=10)
        
        # E. Status Bar
        self.status_bar = ctk.CTkFrame(self, height=30, corner_radius=0, fg_color=("gray80", "gray5"))
        self.status_bar.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10,0))
        
        self.status_label = ctk.CTkLabel(self.status_bar, text="Ready", font=("Segoe UI", 11))
        self.status_label.pack(side="left", padx=20)
        
        from . import __version__
        ctk.CTkLabel(self.status_bar, text=f"v{__version__}", font=("Segoe UI", 11), text_color="gray").pack(side="right", padx=20)

    def add_form_field(self, label_text, var):
        frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        frame.pack(fill="x", pady=5)
        ctk.CTkLabel(frame, text=label_text, width=80, anchor="w").pack(side="left")
        entry = ctk.CTkEntry(frame, textvariable=var)
        entry.pack(side="left", fill="x", expand=True, padx=10)
        return entry

    def toggle_pass_visibility(self):
        if self.pass_entry.cget("show") == "*":
            self.pass_entry.configure(show="")
            self.show_pass_btn.configure(text="🔒")
        else:
            self.pass_entry.configure(show="*")
            self.show_pass_btn.configure(text="👁")

    def toggle_theme(self):
        mode = ctk.get_appearance_mode()
        new_mode = "Light" if mode == "Dark" else "Dark"
        ctk.set_appearance_mode(new_mode)
        self.config.theme = new_mode.lower()
        self.config.save()

    def open_settings(self):
        SettingsDialog(self, self.config)

    def open_manual_connect(self):
        ManualConnectDialog(self, self.handle_manual_connect)

    def handle_manual_connect(self, ip, port, user, pwd, drive):
        self.ip_var.set(ip)
        self.port_var.set(str(port))
        self.user_var.set(user)
        self.pass_var.set(pwd)
        self.drive_var.set(drive)
        self.do_mount()

    def refresh_scan(self):
        self.scan_indicator.configure(text="Refreshing...")
        for child in self.devices_scroll.winfo_children():
            child.destroy()
        self.devices.clear()
        self.discovery.manual_refresh()
        self.after(2000, lambda: self.scan_indicator.configure(text="Scanning..."))

    def on_device_found(self, device: DeviceInfo):
        self.after(0, self._add_device_card, device)

    def on_device_lost(self, name: str):
        self.after(0, self._remove_device_card, name)

    def _add_device_card(self, device: DeviceInfo):
        if device.name in self.devices:
            return
            
        card = ctk.CTkFrame(self.devices_scroll, fg_color=("white", "gray17"), corner_radius=10, border_width=1, border_color=("gray80", "gray25"))
        card.pack(fill="x", pady=5, padx=5)
        
        left = ctk.CTkFrame(card, fg_color="transparent")
        left.pack(side="left", padx=15, pady=15, fill="both", expand=True)
        
        name_lbl = ctk.CTkLabel(left, text=device.name, font=("Segoe UI Semibold", 14))
        name_lbl.pack(anchor="w")
        
        info_lbl = ctk.CTkLabel(left, text=f"{device.ip}:{device.port}", font=("Segoe UI", 12), text_color="gray")
        info_lbl.pack(anchor="w")
        
        right = ctk.CTkFrame(card, fg_color="transparent")
        right.pack(side="right", padx=15, pady=15)
        
        dot = ctk.CTkLabel(right, text="●", text_color=self.success_color, font=("Segoe UI", 16))
        dot.pack(side="left", padx=10)
        
        btn = ctk.CTkButton(right, text="Select", width=70, command=lambda d=device: self.select_device(d))
        btn.pack(side="left")
        
        self.devices[device.name] = {"card": card, "device": device, "btn": btn}
        self.status_label.configure(text=f"Found {len(self.devices)} devices")

    def _remove_device_card(self, name: str):
        if name in self.devices:
            self.devices[name]["card"].destroy()
            del self.devices[name]
            self.status_label.configure(text=f"Found {len(self.devices)} devices")

    def select_device(self, device: DeviceInfo):
        self.selected_device = device
        self.ip_var.set(device.ip)
        self.port_var.set(str(device.port))
        
        # Look for saved credentials
        for sd in self.config.saved_devices:
            if sd.name == device.name:
                self.user_var.set(sd.username)
                self.pass_var.set(self.config.decrypt_password(sd.password_encrypted))
                self.drive_var.set(sd.drive_letter)
                break
                
        # Update UI highlighting
        for name, data in self.devices.items():
            if name == device.name:
                data["card"].configure(border_color=self.accent_color, border_width=2)
            else:
                data["card"].configure(border_color=("gray80", "gray25"), border_width=1)
                
        self.check_mount_status()

    def check_mount_status(self):
        if not self.selected_device:
            return
            
        is_mounted = False
        drive = self.drive_var.get()
        if drive:
            is_mounted = self.mount_manager.is_mounted(drive)
            
        if is_mounted:
            self.mount_btn.pack_forget()
            self.unmount_btn.pack(fill="x", padx=30, pady=10)
        else:
            self.unmount_btn.pack_forget()
            self.mount_btn.pack(fill="x", padx=30, pady=10)

    def do_mount(self):
        ip = self.ip_var.get()
        port = int(self.port_var.get())
        user = self.user_var.get()
        pwd = self.pass_var.get()
        drive = self.drive_var.get()
        
        self.status_label.configure(text="Mounting...")
        self.mount_btn.configure(state="disabled")
        
        def mount_thread():
            success, msg = self.mount_manager.mount(ip, port, user, pwd, drive)
            self.after(0, self.mount_finished, success, msg, drive)
            
        threading.Thread(target=mount_thread, daemon=True).start()

    def mount_finished(self, success, msg, drive):
        self.mount_btn.configure(state="normal")
        if success:
            self.status_label.configure(text=f"Successfully mounted to {drive}:")
            self.check_mount_status()
            self.refresh_mounts_list()
            
            # Save credentials
            if self.selected_device:
                from .config import SavedDevice
                sd = SavedDevice(
                    name=self.selected_device.name,
                    ip=self.selected_device.ip,
                    port=self.selected_device.port,
                    username=self.user_var.get(),
                    password_encrypted=self.config.encrypt_password(self.pass_var.get()),
                    drive_letter=drive
                )
                
                # Update if exists, else append
                found = False
                for i, existing in enumerate(self.config.saved_devices):
                    if existing.name == sd.name:
                        self.config.saved_devices[i] = sd
                        found = True
                        break
                if not found:
                    self.config.saved_devices.append(sd)
                self.config.save()
        else:
            self.status_label.configure(text=f"Mount failed: {msg}")
            # Show error dialog?

    def do_unmount(self):
        drive = self.drive_var.get()
        self.status_label.configure(text="Unmounting...")
        
        def unmount_thread():
            success = self.mount_manager.unmount(drive)
            self.after(0, self.unmount_finished, success, drive)
            
        threading.Thread(target=unmount_thread, daemon=True).start()

    def unmount_finished(self, success, drive):
        if success:
            self.status_label.configure(text=f"Unmounted {drive}:")
            self.check_mount_status()
            self.refresh_mounts_list()
        else:
            self.status_label.configure(text=f"Failed to unmount {drive}:")

    def unmount_all(self):
        mounts = self.mount_manager.get_mounted_drives()
        for m in mounts:
            self.mount_manager.unmount(m.drive_letter)
        self.refresh_mounts_list()
        self.check_mount_status()

    def refresh_mounts_list(self):
        for child in self.mounts_scroll.winfo_children():
            child.destroy()
            
        mounts = self.mount_manager.get_mounted_drives()
        for m in mounts:
            frame = ctk.CTkFrame(self.mounts_scroll, fg_color=("white", "gray17"), height=40, corner_radius=5)
            frame.pack(fill="x", pady=2, padx=2)
            frame.pack_propagate(False)
            
            ctk.CTkLabel(frame, text=f"{m.drive_letter}:\\", font=("Segoe UI Semibold", 12)).pack(side="left", padx=10)
            ctk.CTkLabel(frame, text=m.remote_path, text_color="gray").pack(side="left", padx=10)
            
            ctk.CTkButton(frame, text="Eject", width=60, height=24, fg_color="transparent", border_width=1, text_color=self.error_color,
                         command=lambda d=m.drive_letter: self.mount_manager.unmount(d) or self.refresh_mounts_list()).pack(side="right", padx=5)
                         
            ctk.CTkButton(frame, text="Open", width=60, height=24, 
                         command=lambda d=m.drive_letter: self.mount_manager.open_in_explorer(d)).pack(side="right", padx=5)

    def update_mounts_loop(self):
        self.refresh_mounts_list()
        self.check_mount_status()
        self.after(5000, self.update_mounts_loop)

    def on_close(self):
        self.config.window_geometry = self.geometry()
        self.config.save()
        
        if self.config.minimize_to_tray:
            self.withdraw()
            self.setup_tray()
        else:
            self.quit_app()

    def setup_tray(self):
        try:
            import pystray
            from PIL import Image, ImageDraw
            
            # Generate a simple icon
            image = Image.new('RGB', (64, 64), color = (67, 97, 238))
            d = ImageDraw.Draw(image)
            d.text((16,16), "PD", fill=(255,255,255))
            
            menu = pystray.Menu(
                pystray.MenuItem("Show", self.show_from_tray),
                pystray.MenuItem("Quit", self.quit_from_tray)
            )
            
            self.tray_icon = pystray.Icon("PhoneDrive", image, "PhoneDrive", menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        except ImportError:
            self.quit_app()

    def show_from_tray(self, icon, item):
        icon.stop()
        self.after(0, self.deiconify)

    def quit_from_tray(self, icon, item):
        icon.stop()
        self.after(0, self.quit_app)

    def quit_app(self):
        self.discovery.stop_scanning()
        self.destroy()
        import os
        os._exit(0)
