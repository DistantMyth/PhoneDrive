package com.phonedrive

import android.app.Application
import org.apache.sshd.common.util.OsUtils
import org.apache.sshd.common.util.io.PathUtils

class PhoneDriveApp : Application() {
    override fun onCreate() {
        super.onCreate()
        // Android reports Linux; initialize SSHD before any static crypto probes.
        OsUtils.setAndroid(true)
        OsUtils.setCurrentUser("phonedrive")
        OsUtils.setCurrentWorkingDirectoryResolver { filesDir.toPath() }
        PathUtils.setUserHomeFolderResolver { filesDir.toPath() }
        // Use Android's default JCA providers, not its incomplete legacy BC provider.
        System.setProperty("org.apache.sshd.security.provider.BC.enabled", "false")
        // Set user.home for MINA SSHD compatibility to avoid crashes when generating/loading keys
        System.setProperty("user.home", filesDir.absolutePath)
    }
}
