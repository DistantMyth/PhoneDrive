package com.phonedrive.service

import android.content.Context
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.util.Log

/** All state transitions run on the main looper; stale callbacks cannot win. */
class NsdAdvertiser(
    context: Context,
    private val onStatus: (String) -> Unit = {},
    private val manager: NsdManager = context.getSystemService(Context.NSD_SERVICE) as NsdManager,
    private val handler: Handler = Handler(Looper.getMainLooper())
) {
    private var desiredPort: Int? = null
    private var listener: NsdManager.RegistrationListener? = null
    private var stopping = false
    private var retryDelay = 1_000L
    private val retry = Runnable { registerIfNeeded() }

    fun register(port: Int) {
        if (desiredPort != port) {
            desiredPort = port
            unregisterCurrent()
        }
        registerIfNeeded()
    }

    fun networkChanged() {
        // Android NSD manages address changes; failed registrations need a retry.
        handler.removeCallbacks(retry)
        registerIfNeeded()
    }

    private fun registerIfNeeded() {
        val port = desiredPort ?: return
        if (listener != null || stopping) return
        handler.removeCallbacks(retry)
        val info = NsdServiceInfo().apply {
            serviceName = "PhoneDrive-${Build.MODEL}"
            serviceType = "_sftp-ssh._tcp."
            this.port = port
        }
        // Keep the pre-1.1 service name so existing saved Windows devices match.
        info.serviceName = Build.MODEL
        val attempt = object : NsdManager.RegistrationListener {
            override fun onRegistrationFailed(serviceInfo: NsdServiceInfo, errorCode: Int) {
                handler.post {
                    if (listener !== this) return@post
                    listener = null
                    stopping = false
                    scheduleRetry("Discovery retry ($errorCode)")
                }
            }

            override fun onServiceRegistered(serviceInfo: NsdServiceInfo) {
                handler.post {
                    if (listener !== this) return@post
                    retryDelay = 1_000L
                    if (desiredPort == null) unregisterCurrent()
                    else if (!stopping) onStatus("Discoverable")
                    Log.i(TAG, "Registered ${serviceInfo.serviceName}")
                }
            }

            override fun onServiceUnregistered(serviceInfo: NsdServiceInfo) {
                handler.post {
                    if (listener !== this) return@post
                    listener = null
                    stopping = false
                    registerIfNeeded()
                }
            }

            override fun onUnregistrationFailed(serviceInfo: NsdServiceInfo, errorCode: Int) {
                handler.post {
                    if (listener !== this) return@post
                    stopping = false
                    Log.w(TAG, "Unregister failed: $errorCode")
                    handler.postDelayed({ if (listener === this) unregisterCurrent() }, retryDelay)
                    retryDelay = (retryDelay * 2).coerceAtMost(60_000)
                }
            }
        }
        listener = attempt
        onStatus("Registering discovery")
        try {
            manager.registerService(info, NsdManager.PROTOCOL_DNS_SD, attempt)
        } catch (error: Exception) {
            if (listener === attempt) listener = null
            Log.w(TAG, "Registration failed", error)
            scheduleRetry("Discovery retry")
        }
    }

    private fun scheduleRetry(status: String) {
        if (desiredPort == null) return
        onStatus(status)
        handler.removeCallbacks(retry)
        handler.postDelayed(retry, retryDelay)
        retryDelay = (retryDelay * 2).coerceAtMost(60_000)
    }

    private fun unregisterCurrent() {
        val current = listener ?: return
        if (stopping) return
        stopping = true
        try {
            manager.unregisterService(current)
        } catch (error: IllegalArgumentException) {
            listener = null
            stopping = false
            scheduleRetry("Discovery retry")
        } catch (error: Exception) {
            stopping = false
            Log.w(TAG, "Unregister failed", error)
            handler.postDelayed({ if (listener === current) unregisterCurrent() }, 5_000)
        }
    }

    fun unregister() {
        desiredPort = null
        handler.removeCallbacks(retry)
        unregisterCurrent()
        onStatus("Stopped")
    }

    companion object { private const val TAG = "NsdAdvertiser" }
}
