package com.phonedrive.viewmodel

import android.app.Application
import android.content.Context
import android.content.Intent
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import com.phonedrive.service.ServerSettings
import com.phonedrive.service.SftpServerService

class ServerViewModel(application: Application) : AndroidViewModel(application) {
    private val settings = ServerSettings(application)
    private var config by mutableStateOf(settings.initialize())
    private val prefs = application.getSharedPreferences("ServerPrefs", Context.MODE_PRIVATE)
    private val listener = android.content.SharedPreferences.OnSharedPreferenceChangeListener { _, _ ->
        runCatching { settings.read() }.onSuccess { config = it }
    }
    init { prefs.registerOnSharedPreferenceChangeListener(listener) }
    override fun onCleared() {
        prefs.unregisterOnSharedPreferenceChangeListener(listener)
        super.onCleared()
    }
    val serviceState = SftpServerService.serviceState
    private val busy get() = serviceState.value.isRunning || serviceState.value.isStarting

    var port: Int
        get() = config.port
        set(value) {
            if (!busy && value in 1..65535) {
                config = config.copy(port = value)
                settings.save(config)
            }
        }

    var username: String
        get() = config.username
        set(value) {
            if (!busy && value.isNotBlank() && value.none { it in "\\/@!\r\n" }) {
                config = config.copy(username = value)
                settings.save(config)
            }
        }

    val password: String get() = config.password

    fun regeneratePassword() {
        if (!busy) {
            config = config.copy(password = ServerSettings.generatePassword())
            settings.save(config)
        }
    }

    fun startServer(context: Context) {
        config = settings.read()
        settings.requestedRunning = true
        context.startForegroundService(Intent(context, SftpServerService::class.java))
    }

    fun stopServer(context: Context) {
        settings.requestedRunning = false
        context.stopService(Intent(context, SftpServerService::class.java))
    }
}
