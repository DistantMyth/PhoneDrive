import customtkinter as ctk
import sys
import threading
from .prerequisites import get_status, install_winfsp, install_sshfs_win

class PrereqDialog(ctk.CTk):
    def __init__(self, status):
        super().__init__()
        self.title("PhoneDrive - Prerequisites")
        self.geometry("500x300")
        self.resizable(False, False)
        
        ctk.set_appearance_mode("dark")
        
        self.status = status
        
        self.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(self, text="Missing Requirements", font=("Segoe UI Semibold", 20)).grid(row=0, column=0, pady=(20, 10))
        
        text = "PhoneDrive requires WinFsp and SSHFS-Win to mount your phone as a local drive."
        ctk.CTkLabel(self, text=text, wraplength=400).grid(row=1, column=0, pady=10)
        
        self.winfsp_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.winfsp_frame.grid(row=2, column=0, pady=5, sticky="ew", padx=40)
        ctk.CTkLabel(self.winfsp_frame, text="WinFsp:").pack(side="left")
        
        if status.winfsp_installed:
            ctk.CTkLabel(self.winfsp_frame, text="Installed", text_color="#06d6a0").pack(side="right")
        else:
            ctk.CTkButton(self.winfsp_frame, text="Install via Winget", command=self.do_install_winfsp).pack(side="right")
            
        self.sshfs_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.sshfs_frame.grid(row=3, column=0, pady=5, sticky="ew", padx=40)
        ctk.CTkLabel(self.sshfs_frame, text="SSHFS-Win:").pack(side="left")
        
        if status.sshfs_installed:
            ctk.CTkLabel(self.sshfs_frame, text="Installed", text_color="#06d6a0").pack(side="right")
        else:
            ctk.CTkButton(self.sshfs_frame, text="Install via Winget", command=self.do_install_sshfs).pack(side="right")
            
        self.continue_btn = ctk.CTkButton(self, text="Continue", command=self.destroy)
        self.continue_btn.grid(row=4, column=0, pady=30)
        
        self.update_continue_btn()

    def update_continue_btn(self):
        if self.status.winfsp_installed and self.status.sshfs_installed:
            self.continue_btn.configure(state="normal")
        else:
            self.continue_btn.configure(state="disabled")

    def do_install_winfsp(self):
        def task():
            install_winfsp()
            self.status.winfsp_installed = True
            self.after(0, self.refresh_ui)
        threading.Thread(target=task, daemon=True).start()

    def do_install_sshfs(self):
        def task():
            install_sshfs_win()
            self.status.sshfs_installed = True
            self.after(0, self.refresh_ui)
        threading.Thread(target=task, daemon=True).start()

    def refresh_ui(self):
        for widget in self.winfsp_frame.winfo_children():
            widget.destroy()
        ctk.CTkLabel(self.winfsp_frame, text="WinFsp:").pack(side="left")
        if self.status.winfsp_installed:
            ctk.CTkLabel(self.winfsp_frame, text="Installed", text_color="#06d6a0").pack(side="right")
        else:
            ctk.CTkButton(self.winfsp_frame, text="Install via Winget", command=self.do_install_winfsp).pack(side="right")
            
        for widget in self.sshfs_frame.winfo_children():
            widget.destroy()
        ctk.CTkLabel(self.sshfs_frame, text="SSHFS-Win:").pack(side="left")
        if self.status.sshfs_installed:
            ctk.CTkLabel(self.sshfs_frame, text="Installed", text_color="#06d6a0").pack(side="right")
        else:
            ctk.CTkButton(self.sshfs_frame, text="Install via Winget", command=self.do_install_sshfs).pack(side="right")
            
        self.update_continue_btn()


def main():
    try:
        status = get_status()
        if not status.winfsp_installed or not status.sshfs_installed:
            app = PrereqDialog(status)
            app.mainloop()
            
            # Check again
            status = get_status()
            if not status.winfsp_installed or not status.sshfs_installed:
                print("Missing prerequisites. Exiting.")
                sys.exit(1)
                
        from .gui import MainApp
        app = MainApp()
        app.mainloop()
    except Exception as e:
        import traceback
        import tkinter.messagebox
        tkinter.messagebox.showerror("Fatal Error", f"An unexpected error occurred:\n\n{traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main()
