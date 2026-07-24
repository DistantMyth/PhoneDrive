package com.phonedrive.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.net.wifi.WifiManager
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import androidx.core.app.NotificationCompat
import com.phonedrive.MainActivity
import com.phonedrive.sftp.SftpServerManager
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.net.Inet4Address
import java.net.NetworkInterface

data class ServiceState(
    val isRunning: Boolean = false,
    val ipAddress: String = "127.0.0.1",
    val port: Int = 2222,
    val username: String = "",
    val password: String = "",
    val activeConnections: Int = 0
)

class SftpServerService : Service() {

    private val sftpManager = SftpServerManager()
    private val nsdAdvertiser by lazy { NsdAdvertiser(this) }
    
    private var wakeLock: PowerManager.WakeLock? = null
    private var wifiLock: WifiManager.WifiLock? = null
    private var multicastLock: WifiManager.MulticastLock? = null
    private val serviceJob = Job()
    private val serviceScope = CoroutineScope(Dispatchers.IO + serviceJob)

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val action = intent?.action
        if (action == ACTION_STOP) {
            stopSelf()
            return START_NOT_STICKY
        }

        val port = intent?.getIntExtra(EXTRA_PORT, 2222) ?: 2222
        val username = intent?.getStringExtra(EXTRA_USERNAME) ?: "phone"
        val password = intent?.getStringExtra(EXTRA_PASSWORD) ?: ""

        val ipAddress = getDeviceIpAddress()

        startForeground(NOTIFICATION_ID, createNotification(ipAddress, port, 0))
        acquireLocks()

        try {
            sftpManager.start(port, username, password, filesDir)
            nsdAdvertiser.register(port)
            
            _serviceState.update {
                it.copy(
                    isRunning = true,
                    ipAddress = ipAddress,
                    port = port,
                    username = username,
                    password = password,
                    activeConnections = 0
                )
            }

            serviceScope.launch {
                sftpManager.connectionCount.collect { count ->
                    _serviceState.update { it.copy(activeConnections = count) }
                    val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
                    notificationManager.notify(NOTIFICATION_ID, createNotification(ipAddress, port, count))
                }
            }

        } catch (e: Exception) {
            stopSelf()
        }

        return START_STICKY
    }

    override fun onDestroy() {
        nsdAdvertiser.unregister()
        sftpManager.stop()
        releaseLocks()
        serviceJob.cancel()
        _serviceState.update { it.copy(isRunning = false, activeConnections = 0) }
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun acquireLocks() {
        val powerManager = getSystemService(Context.POWER_SERVICE) as PowerManager
        wakeLock = powerManager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "PhoneDrive::WakeLock").apply {
            acquire(24 * 60 * 60 * 1000L) // 24 hours max
        }

        val wifiManager = applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
        wifiLock = wifiManager.createWifiLock(WifiManager.WIFI_MODE_FULL_HIGH_PERF, "PhoneDrive::WifiLock").apply {
            acquire()
        }
        multicastLock = wifiManager.createMulticastLock("PhoneDrive::MulticastLock").apply {
            setReferenceCounted(true)
            acquire()
        }
    }

    private fun releaseLocks() {
        wakeLock?.let { if (it.isHeld) it.release() }
        wifiLock?.let { if (it.isHeld) it.release() }
        multicastLock?.let { if (it.isHeld) it.release() }
    }

    private fun getDeviceIpAddress(): String {
        try {
            val interfaces = NetworkInterface.getNetworkInterfaces()
            while (interfaces.hasMoreElements()) {
                val networkInterface = interfaces.nextElement()
                if (networkInterface.isLoopback || !networkInterface.isUp) continue
                val addresses = networkInterface.inetAddresses
                while (addresses.hasMoreElements()) {
                    val address = addresses.nextElement()
                    if (!address.isLoopbackAddress && address is Inet4Address) {
                        return address.hostAddress ?: "127.0.0.1"
                    }
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
        return "127.0.0.1"
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "SFTP Server Status",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Shows the status of the SFTP Server"
            }
            val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            manager.createNotificationChannel(channel)
        }
    }

    private fun createNotification(ipAddress: String, port: Int, connections: Int): Notification {
        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP
        }
        val pendingIntent = PendingIntent.getActivity(
            this, 0, intent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        val stopIntent = Intent(this, SftpServerService::class.java).apply {
            action = ACTION_STOP
        }
        val stopPendingIntent = PendingIntent.getService(
            this, 1, stopIntent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("PhoneDrive SFTP Server")
            .setContentText("Running at sftp://$ipAddress:$port")
            .setSubText("Clients connected: $connections")
            .setSmallIcon(android.R.drawable.stat_sys_data_bluetooth) // Fallback icon
            .setContentIntent(pendingIntent)
            .addAction(android.R.drawable.ic_menu_close_clear_cancel, "Stop", stopPendingIntent)
            .setOngoing(true)
            .build()
    }

    companion object {
        private const val CHANNEL_ID = "SftpServerChannel"
        private const val NOTIFICATION_ID = 1
        
        const val ACTION_STOP = "com.phonedrive.action.STOP"
        const val EXTRA_PORT = "EXTRA_PORT"
        const val EXTRA_USERNAME = "EXTRA_USERNAME"
        const val EXTRA_PASSWORD = "EXTRA_PASSWORD"

        private val _serviceState = MutableStateFlow(ServiceState())
        val serviceState: StateFlow<ServiceState> = _serviceState.asStateFlow()
    }
}
