package com.phonedrive.service

import android.annotation.SuppressLint
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.net.ConnectivityManager
import android.net.LinkProperties
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import android.net.wifi.WifiManager
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.PowerManager
import android.util.Log
import androidx.core.app.NotificationCompat
import com.phonedrive.MainActivity
import com.phonedrive.sftp.SftpServerManager
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.net.Inet4Address
import java.net.NetworkInterface
import java.util.concurrent.Executors

data class ServiceState(
    val isRunning: Boolean = false,
    val isStarting: Boolean = false,
    val ipAddress: String = "127.0.0.1",
    val port: Int = 2222,
    val username: String = "",
    val password: String = "",
    val activeConnections: Int = 0,
    val batteryExempt: Boolean = false,
    val discoveryStatus: String = "Stopped",
    val error: String? = null
) {
    override fun toString() = "ServiceState(running=$isRunning, starting=$isStarting, ip=$ipAddress, clients=$activeConnections)"
}

class SftpServerService : Service() {
    private val manager = SftpServerManager()
    private val handler = Handler(Looper.getMainLooper())
    private val worker = Executors.newSingleThreadExecutor()
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    private val settings by lazy { ServerSettings(this) }
    private val power by lazy { getSystemService(Context.POWER_SERVICE) as PowerManager }
    private val connectivity by lazy { getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager }
    private val advertiser by lazy { NsdAdvertiser(applicationContext, onStatus = { status ->
        _serviceState.update { it.copy(discoveryStatus = status) }
    }) }
    private var wakeLock: PowerManager.WakeLock? = null
    private var wifiLock: WifiManager.WifiLock? = null
    private var multicastLock: WifiManager.MulticastLock? = null
    private var networkRegistered = false
    private var startQueued = false
    @Volatile private var destroyed = false
    private val networkCallback = object : ConnectivityManager.NetworkCallback() {
        override fun onAvailable(network: Network) = networkChanged()
        override fun onLost(network: Network) = networkChanged()
        override fun onLinkPropertiesChanged(network: Network, properties: LinkProperties) = networkChanged()
    }
    private val refresh = object : Runnable {
        override fun run() {
            if (destroyed) return
            refreshNetworkAndPower()
            handler.postDelayed(this, 30_000) // Also covers hotspot/interface changes.
        }
    }

    override fun onCreate() {
        super.onCreate()
        val notifications = getSystemService(NotificationManager::class.java)
        notifications.createNotificationChannel(NotificationChannel(CHANNEL_ID, "PhoneDrive connection", NotificationManager.IMPORTANCE_LOW))
        scope.launch {
            manager.connectionCount.collect { count ->
                _serviceState.update { it.copy(activeConnections = count) }
                if (_serviceState.value.isRunning) updateNotification()
            }
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            settings.requestedRunning = false
            Log.i(TAG, "Stop requested")
            stopSelf()
            return START_NOT_STICKY
        }
        // A null-intent restart uses exactly the persisted configuration, and
        // an explicit stop cannot be undone by a delayed start command.
        if (!settings.requestedRunning) {
            stopSelf()
            return START_NOT_STICKY
        }
        val config = try { settings.read() } catch (error: Exception) {
            failStart(error)
            return START_NOT_STICKY
        }
        startForeground(NOTIFICATION_ID, createNotification())
        if (startQueued || _serviceState.value.isRunning) return START_STICKY
        startQueued = true
        _serviceState.value = ServiceState(isStarting = true, port = config.port,
            username = config.username, password = config.password)
        try {
            acquireLocks()
            connectivity.registerNetworkCallback(NetworkRequest.Builder().clearCapabilities()
                .addTransportType(NetworkCapabilities.TRANSPORT_WIFI).build(), networkCallback)
            networkRegistered = true
            handler.post(refresh)
        } catch (error: Exception) {
            failStart(error)
            return START_NOT_STICKY
        }
        Log.i(TAG, "Start requested; recreated=${intent == null}, port=${config.port}")
        worker.execute {
            try {
                if (destroyed || !settings.requestedRunning) return@execute
                manager.start(config.port, config.username, config.password, filesDir)
                if (destroyed || !settings.requestedRunning) {
                    manager.stop()
                    return@execute
                }
                handler.post {
                    if (!destroyed && settings.requestedRunning) {
                        startQueued = false
                        _serviceState.update { it.copy(isStarting = false, isRunning = true) }
                        advertiser.register(config.port)
                        refreshNetworkAndPower()
                    }
                }
            } catch (error: LinkageError) {
                handler.post { if (!destroyed) failStart(IllegalStateException("SSH runtime initialization failed", error)) }
            } catch (error: Exception) {
                handler.post { if (!destroyed) failStart(error) }
            }
        }
        return START_STICKY
    }

    private fun failStart(error: Exception) {
        Log.e(TAG, "Unable to start server", error)
        settings.requestedRunning = false
        _serviceState.update { it.copy(isStarting = false, isRunning = false,
            password = "", error = error.message ?: "Could not start server") }
        stopSelf()
    }

    private fun networkChanged() {
        handler.post {
            if (!destroyed) {
                refreshNetworkAndPower()
                if (_serviceState.value.isRunning) advertiser.networkChanged()
            }
        }
    }

    private fun refreshNetworkAndPower() {
        val ip = deviceIpAddress()
        val exempt = power.isIgnoringBatteryOptimizations(packageName)
        val previous = _serviceState.value
        _serviceState.update { it.copy(ipAddress = ip, batteryExempt = exempt) }
        if (previous.ipAddress != ip || previous.batteryExempt != exempt) {
            Log.i(TAG, "Network/power changed: ip=$ip, exempt=$exempt, idle=${power.isDeviceIdleMode}, interactive=${power.isInteractive}, wake=${wakeLock?.isHeld}")
        }
        updateNotification()
    }

    @SuppressLint("WakelockTimeout")
    @Suppress("DEPRECATION")
    private fun acquireLocks() {
        // The user explicitly starts this persistent foreground server. Its
        // lifetime, not an arbitrary 24-hour timer, owns the partial wake lock.
        if (wakeLock == null) wakeLock = power.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "PhoneDrive::Server").apply {
            setReferenceCounted(false)
            acquire()
        }
        val wifi = applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
        if (Build.VERSION.SDK_INT < 34 && wifiLock == null) {
            wifiLock = wifi.createWifiLock(WifiManager.WIFI_MODE_FULL_HIGH_PERF, "PhoneDrive::Wifi").apply {
                setReferenceCounted(false)
                acquire()
            }
        }
        // API 34 remaps HIGH_PERF to a screen-on-only mode; it cannot provide
        // a background guarantee. Network monitoring and recovery are required.
        if (multicastLock == null) multicastLock = wifi.createMulticastLock("PhoneDrive::Discovery").apply {
            setReferenceCounted(false)
            acquire()
        }
    }

    private fun deviceIpAddress(): String {
        return try {
            connectivity.allNetworks.firstNotNullOfOrNull { network ->
                if (connectivity.getNetworkCapabilities(network)?.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) == true) {
                    connectivity.getLinkProperties(network)?.linkAddresses?.map { it.address }
                        ?.filterIsInstance<Inet4Address>()?.firstOrNull { !it.isLoopbackAddress }?.hostAddress
                } else null
            } ?: NetworkInterface.getNetworkInterfaces().toList()
                .filter { it.isUp && !it.isLoopback && it.name.matches(Regex("(wlan|wifi|ap|swlan|softap|rndis|eth).*")) }
                .flatMap { it.inetAddresses.toList() }.filterIsInstance<Inet4Address>()
                .firstOrNull { !it.isLoopbackAddress && !it.isLinkLocalAddress }?.hostAddress ?: "127.0.0.1"
        } catch (error: Exception) {
            Log.w(TAG, "Could not inspect local network", error)
            "127.0.0.1"
        }
    }

    override fun onDestroy() {
        destroyed = true
        handler.removeCallbacksAndMessages(null)
        if (networkRegistered) runCatching { connectivity.unregisterNetworkCallback(networkCallback) }
        advertiser.unregister()
        scope.cancel()
        worker.execute { manager.stop() }
        worker.shutdown()
        wakeLock?.let { if (it.isHeld) it.release() }
        wifiLock?.let { if (it.isHeld) it.release() }
        multicastLock?.let { if (it.isHeld) it.release() }
        _serviceState.update { it.copy(isRunning = false, isStarting = false, password = "", activeConnections = 0, discoveryStatus = "Stopped") }
        stopForeground(STOP_FOREGROUND_REMOVE)
        Log.i(TAG, "Service destroyed; requestedRunning=${settings.requestedRunning}")
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun updateNotification() {
        getSystemService(NotificationManager::class.java).notify(NOTIFICATION_ID, createNotification())
    }

    private fun createNotification(): Notification {
        val state = _serviceState.value
        val open = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val stop = PendingIntent.getService(this, 1, Intent(this, SftpServerService::class.java).setAction(ACTION_STOP), PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("PhoneDrive")
            .setContentText(if (state.isStarting) "Starting server…" else if (state.ipAddress == "127.0.0.1") "Waiting for Wi-Fi or hotspot" else "sftp://${state.ipAddress}:${state.port}")
            .setSubText("Connected clients: ${state.activeConnections}")
            .setSmallIcon(android.R.drawable.stat_sys_upload)
            .setContentIntent(open).addAction(android.R.drawable.ic_menu_close_clear_cancel, "Stop", stop)
            .setOnlyAlertOnce(true).setOngoing(true).build()
    }

    companion object {
        private const val TAG = "SftpServerService"
        private const val CHANNEL_ID = "SftpServerChannel"
        private const val NOTIFICATION_ID = 1
        const val ACTION_STOP = "com.phonedrive.action.STOP"
        private val _serviceState = MutableStateFlow(ServiceState())
        val serviceState: StateFlow<ServiceState> = _serviceState.asStateFlow()
    }
}
