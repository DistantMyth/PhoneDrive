# Changelog

## 1.1.0

- Keep the Windows mount recovery worker alive through screen-off, mDNS gaps, endpoint outages, and disconnected drive mappings.
- Use Win32 network mapping APIs with exact remote identity checks and DPAPI-protected saved credentials.
- Keep the Android SFTP service in the foreground with persisted settings, network callbacks, bounded SSH keepalives, and restart recovery.
- Add reliability tests, structured logging, safer backup rules, and reproducible Android/Windows release builds.
