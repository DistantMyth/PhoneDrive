package com.phonedrive

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.phonedrive.sftp.SftpServerManager
import org.apache.sshd.client.SshClient
import org.apache.sshd.common.util.ExceptionUtils
import org.apache.sshd.common.util.OsUtils
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.net.ServerSocket

/** Runs on ART: desktop JVM tests cannot detect missing Android Java classes. */
@RunWith(AndroidJUnit4::class)
class SshRuntimeTest {
    @Test fun cryptoInitializationAndServerRestartWorkOnAndroid() {
        assertTrue(OsUtils.isAndroid())
        val original = IllegalArgumentException("probe")
        assertSame(original, ExceptionUtils.peelException(original))
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val manager = SftpServerManager()
        val port = ServerSocket(0).use { it.localPort }
        repeat(2) {
            try {
                manager.start(port, "runtime-test", "test-only-password", context.cacheDir)
                SshClient.setUpDefaultClient().use { client ->
                    client.start()
                    client.connect("runtime-test", "127.0.0.1", port).verify(10_000).session.use { session ->
                        session.addPasswordIdentity("test-only-password")
                        session.auth().verify(10_000)
                        assertTrue(session.isAuthenticated)
                    }
                }
            } finally {
                manager.stop()
            }
        }
    }
}
