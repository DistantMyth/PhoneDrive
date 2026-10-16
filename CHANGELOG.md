# Changelog

## 1.1.1

- Replace the Windows ZIP release with a versioned installer, Start menu shortcuts, an Installed Apps entry, in-place upgrades, and an uninstaller that preserves saved settings.
- Add Windows executable version metadata, single-instance protection, and downgrade prevention.
- Fix the Android power-button crash by initializing SSHD's Android runtime hooks before crypto initialization and using Android's default cryptographic providers.
- Report SSH runtime linkage failures as startup errors instead of terminating the app process.
- Correct the SSH global-request keepalive packet so idle clients remain connected.
- Add a device test for crypto initialization, authentication, and server restart on Android.

## 1.1.0

- Keep the Windows mount recovery worker alive through screen-off, mDNS gaps, endpoint outages, and disconnected drive mappings.
- Use Win32 network mapping APIs with exact remote identity checks and DPAPI-protected saved credentials.
- Keep the Android SFTP service in the foreground with persisted settings, network callbacks, bounded SSH keepalives, and restart recovery.
- Add reliability tests, structured logging, safer backup rules, and reproducible Android/Windows release builds.
