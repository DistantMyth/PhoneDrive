package com.phonedrive.viewmodel

import android.app.Application
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.lifecycle.AndroidViewModel
import com.phonedrive.service.SftpServerService
import kotlinx.coroutines.flow.StateFlow
import com.phonedrive.service.ServiceState
import java.security.SecureRandom

class ServerViewModel(application: Application) : AndroidViewModel(application) {

    private val prefs = application.getSharedPreferences("ServerPrefs", Context.MODE_PRIVATE)

    val serviceState: StateFlow<ServiceState> = SftpServerService.serviceState

    var port: Int
        get() = prefs.getInt("port", 2222)
        set(value) = prefs.edit().putInt("port", value).apply()

    var username: String
        get() = prefs.getString("username", "phone") ?: "phone"
        set(value) = prefs.edit().putString("username", value).apply()

    var password: String
        get() {
            var pwd = prefs.getString("password", null)
            if (pwd == null) {
                pwd = generatePassword()
                prefs.edit().putString("password", pwd).apply()
            }
            return pwd
        }
        set(value) = prefs.edit().putString("password", value).apply()

    fun regeneratePassword() {
        password = generatePassword()
    }

    private fun generatePassword(): String {
        val chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        val random = SecureRandom()
        val sb = StringBuilder(8)
        for (i in 0 until 8) {
            sb.append(chars[random.nextInt(chars.length)])
        }
        return sb.toString()
    }

    fun startServer(context: Context) {
        val intent = Intent(context, SftpServerService::class.java).apply {
            putExtra(SftpServerService.EXTRA_PORT, port)
            putExtra(SftpServerService.EXTRA_USERNAME, username)
            putExtra(SftpServerService.EXTRA_PASSWORD, password)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            context.startForegroundService(intent)
        } else {
            context.startService(intent)
        }
    }

    fun stopServer(context: Context) {
        val intent = Intent(context, SftpServerService::class.java)
        context.stopService(intent)
    }
}
