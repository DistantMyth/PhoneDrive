package com.phonedrive.service

import android.content.Context
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [28])
class ServerSettingsTest {
    private lateinit var context: Context
    @Before fun setup() {
        context = RuntimeEnvironment.getApplication()
        context.getSharedPreferences("ServerPrefs", Context.MODE_PRIVATE).edit().clear().commit()
    }

    @Test fun recreatedServiceReadsSamePortUserAndPassword() {
        val first = ServerSettings(context)
        val config = ServerConfig(8123, "custom", "secret-password")
        first.save(config)
        first.requestedRunning = true
        val recreated = ServerSettings(context)
        assertTrue(recreated.requestedRunning)
        assertEquals(config, recreated.read())
    }

    @Test fun missingCredentialFailsClosedOnServiceRestart() {
        assertThrows(IllegalStateException::class.java) { ServerSettings(context).read() }
        assertFalse(ServerSettings(context).requestedRunning)
    }

    @Test fun explicitStopSurvivesRecreation() {
        val settings = ServerSettings(context)
        settings.initialize()
        settings.requestedRunning = true
        settings.requestedRunning = false
        assertFalse(ServerSettings(context).requestedRunning)
    }

    @Test fun passwordIsGeneratedOnceAndNeverPrinted() {
        val settings = ServerSettings(context)
        val first = settings.initialize()
        assertEquals(16, first.password.length)
        assertEquals(first, ServerSettings(context).initialize())
        assertFalse(first.toString().contains(first.password))
    }

    @Test fun blankCredentialsAndInvalidPortsAreRejected() {
        assertThrows(IllegalArgumentException::class.java) { ServerConfig(2222, "phone", "") }
        assertThrows(IllegalArgumentException::class.java) { ServerConfig(2222, "", "password") }
        assertThrows(IllegalArgumentException::class.java) { ServerConfig(0, "phone", "password") }
        assertThrows(IllegalArgumentException::class.java) { ServerConfig(65536, "phone", "password") }
    }
}
