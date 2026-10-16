package com.phonedrive.service

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED ||
            intent.action == Intent.ACTION_MY_PACKAGE_REPLACED) {
            
            val settings = ServerSettings(context)
            if (settings.requestedRunning) runCatching {
                settings.read()
                context.startForegroundService(Intent(context, SftpServerService::class.java))
            }.onFailure { android.util.Log.e("BootReceiver", "Could not restore server", it) }
        }
    }
}
