package com.phonedrive.service

import android.content.Context
import java.security.SecureRandom

data class ServerConfig(val port: Int, val username: String, val password: String) {
    init {
        require(port in 1..65535) { "Port must be between 1 and 65535" }
        require(username.isNotBlank() && username.none { it in "\\/@!\r\n" }) { "Invalid username" }
        require(password.isNotBlank()) { "Password must not be empty" }
    }

    override fun toString() = "ServerConfig(port=$port, username=$username, password=<redacted>)"
}

class ServerSettings(context: Context) {
    private val prefs = context.getSharedPreferences("ServerPrefs", Context.MODE_PRIVATE)

    var requestedRunning: Boolean
        get() = prefs.getBoolean("requested_running", false)
        set(value) { check(prefs.edit().putBoolean("requested_running", value).commit()) }

    fun read(): ServerConfig = ServerConfig(
        prefs.getInt("port", 2222), prefs.getString("username", "phone") ?: "phone",
        prefs.getString("password", null) ?: error("Open PhoneDrive to configure a password")
    )

    fun initialize(): ServerConfig {
        // Only an explicit app launch creates a credential, never a service restart.
        if (prefs.getString("password", null).isNullOrBlank()) {
            val config = ServerConfig(prefs.getInt("port", 2222).coerceIn(1, 65535),
                prefs.getString("username", "phone")?.takeIf { it.isNotBlank() } ?: "phone", generatePassword())
            save(config)
        }
        return read()
    }

    fun save(config: ServerConfig) {
        check(prefs.edit().putInt("port", config.port).putString("username", config.username)
            .putString("password", config.password).commit()) { "Could not save server settings" }
    }

    companion object {
        fun generatePassword(): String {
            val alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
            val random = SecureRandom()
            return (1..16).map { alphabet[random.nextInt(alphabet.length)] }.joinToString("")
        }
    }
}
