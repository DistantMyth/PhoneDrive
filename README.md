# PhoneDrive

**Your phone, natively integrated into your desktop file manager.**

PhoneDrive is a seamless, two-part application that securely exposes your Android phone's storage over your local network and automatically mounts it as a native drive letter (e.g., `P:\`) in Windows. 

No cables, no cloud syncing, no manual IP typing. Just tap the button on your phone, and it instantly appears in Windows Explorer.

## Features
- **True Native Mounting:** Uses SSHFS-Win to mount your phone as a standard Windows drive. You can drag, drop, stream video, and edit files directly on your phone using Windows apps.
- **Zero Configuration:** The phone advertises its presence via mDNS (zeroconf). The Windows app automatically discovers it, even if your phone's IP address changes when switching from WiFi to a hotspot.
- **Background Persistence:** The Android app runs a secure foreground service (with WakeLock and WifiLock) so the connection stays alive even when your phone is asleep.
- **Fast and Secure:** Built on Apache MINA SSHD and BouncyCastle cryptography, all transfers are encrypted locally over your network.
- **Premium UI:** Both apps feature rich, modern dark-mode interfaces (Material 3 on Android, CustomTkinter on Windows).

## Project Structure

This repository contains both the Android Server and the Windows Client.

### `/android` - PhoneDrive Android Server
A modern Android application built with Kotlin and Jetpack Compose.
- Implements an SFTP server using Apache MINA SSHD.
- Bypasses Android's crippled cryptography engine by injecting a full BouncyCastle provider to ensure crash-free execution.
- Broadcasts the `_sftp-ssh._tcp` service over mDNS (NSD API).
- Requests `MANAGE_EXTERNAL_STORAGE` to provide full access to the device's internal storage (`/storage/emulated/0/`).

### `/windows` - PhoneDrive Desktop Client
A Windows application built with Python and CustomTkinter.
- Listens for mDNS broadcasts using `python-zeroconf` to automatically discover the phone.
- Uses `WinFsp` and `SSHFS-Win` to securely mount the SFTP server.
- Supports auto-mounting when the phone is detected on the network.
- Can run silently in the system tray and start with Windows.

## Getting Started

### 1. Android App
- Build the Android app using Gradle or Android Studio (`android/app/build.gradle.kts`).
- Or install the provided APK directly to your device.
- Open the app, grant the requested "All Files Access" permission, and tap the big power button to start the server.

### 2. Windows App
The Windows application requires Python 3.10+ and a few system prerequisites.

#### Prerequisites
- Install **WinFsp** and **SSHFS-Win**.
  - You can install them via winget:
    ```cmd
    winget install -e --id WinFsp.WinFsp
    winget install -e --id SSHFS-Win.SSHFS-Win
    ```

#### Running the App
1. Navigate to the `windows` directory.
2. Install the required Python packages:
   ```cmd
   pip install -r requirements.txt
   ```
3. Run the application:
   ```cmd
   python main.py
   ```

## Known Issues & Notes
- **Firewall:** Ensure your Windows Firewall allows Python to communicate over private networks for the mDNS discovery to function.
- **Battery Optimization:** For uninterrupted large file transfers, it is recommended to exclude the PhoneDrive Android app from battery optimization in your phone's settings.

## Credits
- Built with [Apache MINA SSHD](https://mina.apache.org/sshd-project/)
- Native mounting powered by [SSHFS-Win](https://github.com/winfsp/sshfs-win) and [WinFsp](https://winfsp.dev/)
- Android UI powered by Jetpack Compose
- Windows UI powered by [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)