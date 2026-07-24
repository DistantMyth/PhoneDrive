package com.phonedrive.sftp

import android.os.Environment
import android.util.Log
import org.apache.sshd.server.SshServer
import org.apache.sshd.server.auth.password.PasswordAuthenticator
import org.apache.sshd.server.keyprovider.SimpleGeneratorHostKeyProvider
import org.apache.sshd.sftp.server.SftpSubsystemFactory
import java.io.File
import java.nio.file.Paths
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.util.concurrent.atomic.AtomicInteger

class SftpServerManager {

    private var sshd: SshServer? = null
    private val activeSessions = AtomicInteger(0)
    private val _connectionCount = MutableStateFlow(0)
    val connectionCount: StateFlow<Int> = _connectionCount.asStateFlow()

    @Synchronized
    fun start(port: Int, username: String, password: String, filesDir: File) {
        if (sshd != null) return

        try {
            sshd = SshServer.setUpDefaultServer()
            sshd?.port = port

            // Host key setup (ED25519)
            val hostKeyFile = File(filesDir, "hostkey.ser")
            sshd?.keyPairProvider = SimpleGeneratorHostKeyProvider(hostKeyFile.toPath())

            // Setup password authentication
            sshd?.passwordAuthenticator = PasswordAuthenticator { u, p, _ ->
                u == username && p == password
            }

            // Map SFTP to Android shared storage
            val externalStoragePath = Environment.getExternalStorageDirectory().absolutePath
            sshd?.fileSystemFactory = AndroidFileSystemFactory(externalStoragePath)

            // Enable SFTP subsystem
            val sftpFactory = SftpSubsystemFactory.Builder().build()
            sshd?.subsystemFactories = listOf(sftpFactory)

            // Listener to update connection count
            sshd?.addSessionListener(object : org.apache.sshd.common.session.SessionListener {
                override fun sessionCreated(session: org.apache.sshd.common.session.Session?) {
                    _connectionCount.value = activeSessions.incrementAndGet()
                }

                override fun sessionClosed(session: org.apache.sshd.common.session.Session?) {
                    val count = activeSessions.decrementAndGet()
                    _connectionCount.value = if (count < 0) {
                        activeSessions.set(0)
                        0
                    } else {
                        count
                    }
                }
            })

            sshd?.start()
            Log.d(TAG, "SFTP Server started on port $port")
        } catch (e: Exception) {
            Log.e(TAG, "Error starting SFTP server", e)
            stop()
            throw e
        }
    }

    @Synchronized
    fun stop() {
        try {
            sshd?.stop(true)
            sshd = null
            activeSessions.set(0)
            _connectionCount.value = 0
            Log.d(TAG, "SFTP Server stopped")
        } catch (e: Exception) {
            Log.e(TAG, "Error stopping SFTP server", e)
        }
    }

    companion object {
        private const val TAG = "SftpServerManager"
    }
}
