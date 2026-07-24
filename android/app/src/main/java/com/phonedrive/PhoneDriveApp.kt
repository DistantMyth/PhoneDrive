package com.phonedrive

import android.app.Application

class PhoneDriveApp : Application() {
    override fun onCreate() {
        super.onCreate()
        // Set user.home for MINA SSHD compatibility to avoid crashes when generating/loading keys
        System.setProperty("user.home", filesDir.absolutePath)
    }
}
