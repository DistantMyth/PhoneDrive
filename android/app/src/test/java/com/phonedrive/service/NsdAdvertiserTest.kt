package com.phonedrive.service

import android.content.Context
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.os.Looper
import java.time.Duration
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import org.mockito.ArgumentMatchers.*
import org.mockito.Mockito.*
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.Shadows.shadowOf
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [28])
class NsdAdvertiserTest {
    @Test fun failureRetriesAndOldCallbacksCannotClearNewRegistration() {
        val manager = mock(NsdManager::class.java)
        val attempts = mutableListOf<NsdManager.RegistrationListener>()
        doAnswer { call -> attempts.add(call.getArgument(2)); null }.`when`(manager)
            .registerService(any(NsdServiceInfo::class.java), anyInt(), any(NsdManager.RegistrationListener::class.java))
        val context: Context = RuntimeEnvironment.getApplication()
        val advertiser = NsdAdvertiser(context, manager = manager)
        advertiser.register(2222)
        assertEquals(1, attempts.size)
        attempts[0].onRegistrationFailed(NsdServiceInfo(), 0)
        shadowOf(Looper.getMainLooper()).idleFor(Duration.ofSeconds(1))
        assertEquals(2, attempts.size)
        attempts[0].onRegistrationFailed(NsdServiceInfo(), 0)
        shadowOf(Looper.getMainLooper()).idleFor(Duration.ofSeconds(10))
        advertiser.register(2222)
        assertEquals(2, attempts.size)
        advertiser.unregister()
    }

    @Test fun stopCancelsPendingRetry() {
        val manager = mock(NsdManager::class.java)
        val attempts = mutableListOf<NsdManager.RegistrationListener>()
        doAnswer { call -> attempts.add(call.getArgument(2)); null }.`when`(manager)
            .registerService(any(NsdServiceInfo::class.java), anyInt(), any(NsdManager.RegistrationListener::class.java))
        val advertiser = NsdAdvertiser(RuntimeEnvironment.getApplication(), manager = manager)
        advertiser.register(2222)
        attempts[0].onRegistrationFailed(NsdServiceInfo(), 0)
        shadowOf(Looper.getMainLooper()).idle()
        advertiser.unregister()
        shadowOf(Looper.getMainLooper()).idleFor(Duration.ofMinutes(2))
        assertEquals(1, attempts.size)
    }
}
