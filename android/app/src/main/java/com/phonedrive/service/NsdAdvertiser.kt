package com.phonedrive.service

import android.content.Context
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.os.Build
import android.util.Log

class NsdAdvertiser(context: Context) {

    private val nsdManager = context.getSystemService(Context.NSD_SERVICE) as NsdManager
    private var registrationListener: NsdManager.RegistrationListener? = null

    private val serviceName = Build.MODEL ?: "PhoneDrive"

    fun register(port: Int) {
        if (registrationListener != null) return

        val serviceInfo = NsdServiceInfo().apply {
            this.serviceName = this@NsdAdvertiser.serviceName
            this.serviceType = "_sftp-ssh._tcp"
            this.port = port
        }

        registrationListener = object : NsdManager.RegistrationListener {
            override fun onRegistrationFailed(serviceInfo: NsdServiceInfo, errorCode: Int) {
                Log.e(TAG, "mDNS Registration failed: $errorCode")
            }

            override fun onUnregistrationFailed(serviceInfo: NsdServiceInfo, errorCode: Int) {
                Log.e(TAG, "mDNS Unregistration failed: $errorCode")
            }

            override fun onServiceRegistered(NsdServiceInfo: NsdServiceInfo) {
                Log.d(TAG, "mDNS Service registered successfully: ${NsdServiceInfo.serviceName}")
            }

            override fun onServiceUnregistered(arg0: NsdServiceInfo) {
                Log.d(TAG, "mDNS Service unregistered")
            }
        }

        try {
            nsdManager.registerService(serviceInfo, NsdManager.PROTOCOL_DNS_SD, registrationListener)
        } catch (e: Exception) {
            Log.e(TAG, "Error registering mDNS service", e)
        }
    }

    fun unregister() {
        try {
            registrationListener?.let {
                nsdManager.unregisterService(it)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error unregistering mDNS service", e)
        } finally {
            registrationListener = null
        }
    }

    companion object {
        private const val TAG = "NsdAdvertiser"
    }
}
