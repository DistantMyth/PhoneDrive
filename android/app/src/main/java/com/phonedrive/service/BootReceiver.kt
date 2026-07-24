package com.phonedrive.service

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED ||
            intent.action == Intent.ACTION_MY_PACKAGE_REPLACED) {
            
            val prefs = context.getSharedPreferences("ServerPrefs", Context.MODE_PRIVATE)
            val autoStart = prefs.getBoolean("auto_start", true) // Default ON
            
            if (autoStart) {
                val port = prefs.getInt("port", 2222)
                val username = prefs.getString("username", "phone") ?: "phone"
                val password = prefs.getString("password", null)
                
                if (password != null) {
                    val serviceIntent = Intent(context, SftpServerService::class.java).apply {
                        putExtra(SftpServerService.EXTRA_PORT, port)
                        putExtra(SftpServerService.EXTRA_USERNAME, username)
                        putExtra(SftpServerService.EXTRA_PASSWORD, password)
                    }
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        context.startForegroundService(serviceIntent)
                    } else {
                        context.startService(serviceIntent)
                    }
                }
            }
        }
    }
}
