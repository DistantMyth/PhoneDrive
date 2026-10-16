package com.phonedrive.sftp

import android.os.Environment
import android.util.Log
import org.apache.sshd.server.SshServer
import org.apache.sshd.server.auth.password.PasswordAuthenticator
import org.apache.sshd.server.keyprovider.SimpleGeneratorHostKeyProvider
import org.apache.sshd.sftp.server.SftpSubsystemFactory
import java.io.File
import com.phonedrive.service.ServerConfig
import org.apache.sshd.common.session.Session
import org.apache.sshd.common.session.SessionListener
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.util.concurrent.ConcurrentHashMap

class SftpServerManager {

    private var sshd: SshServer? = null
    private val activeSessions = ConcurrentHashMap.newKeySet<Session>()
    private var sessionPolicy: SshSessionPolicy? = null
    private val _connectionCount = MutableStateFlow(0)
    val connectionCount: StateFlow<Int> = _connectionCount.asStateFlow()

    @Synchronized
    fun start(port: Int, username: String, password: String, filesDir: File) {
        ServerConfig(port, username, password) // Fail closed even for non-UI callers.
        if (sshd != null) return

        try {
            sshd = SshServer.setUpDefaultServer()
            sshd?.port = port

            // Keep the existing host key stable across service/process restarts.
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
            sessionPolicy = SshSessionPolicy(onUnresponsive = {
                Log.w(TAG, "Closing unresponsive SSH peer ${it.remoteAddress}")
            }).also { it.install(requireNotNull(sshd)) }

            // Listener to update connection count
            sshd?.addSessionListener(object : org.apache.sshd.common.session.SessionListener {
                override fun sessionEvent(session: Session, event: SessionListener.Event) {
                    if (event == SessionListener.Event.Authenticated) {
                        activeSessions.add(session)
                        _connectionCount.value = activeSessions.size
                        Log.i(TAG, "SSH client authenticated: ${session.remoteAddress}")
                    }
                }

                override fun sessionClosed(session: Session) {
                    activeSessions.remove(session)
                    _connectionCount.value = activeSessions.size
                    Log.i(TAG, "SSH session closed: ${session.remoteAddress}; timeout=${session.timeoutStatus}")
                }

                override fun sessionException(session: Session, error: Throwable) {
                    Log.w(TAG, "SSH session failed: ${session.remoteAddress}", error)
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
            sessionPolicy?.close()
            sshd?.stop(true)
            Log.d(TAG, "SFTP Server stopped")
        } catch (e: Exception) {
            Log.e(TAG, "Error stopping SFTP server", e)
        } finally {
            sessionPolicy = null
            sshd = null
            activeSessions.clear()
            _connectionCount.value = 0
        }
    }

    companion object {
        private const val TAG = "SftpServerManager"
    }
}
