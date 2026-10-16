# Android release checks

Run the unit suite and the device suite with an Android device connected:

```sh
./gradlew testDebugUnitTest connectedDebugAndroidTest assembleRelease
```

`SshRuntimeTest` initializes the real application on Android, exercises exception handling, starts the SSH server, authenticates a client, and restarts the server. This catches Android class-loading and crypto-provider failures that a desktop JVM cannot reproduce.

Before publishing the signed release APK, install that exact APK and check:

1. Start, stop, and restart using the power button; confirm no process crash.
2. Authenticate from another device and upload/download a temporary file; compare its hash.
3. Turn the physical screen off for at least six minutes, keep one SFTP connection idle, and transfer files on a second connection. Confirm both original connections still work afterward.
4. Stop the server and confirm the port closes; restart and confirm authentication works again.

Keep credentials out of logs and remove temporary transfer files after validation. Screen-off testing on one phone does not cover every vendor's long-term process restrictions.
