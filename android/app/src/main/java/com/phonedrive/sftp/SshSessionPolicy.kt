package com.phonedrive.sftp

import org.apache.sshd.common.session.Session
import org.apache.sshd.common.session.SessionListener
import org.apache.sshd.common.SshConstants
import org.apache.sshd.core.CoreModuleProperties
import org.apache.sshd.server.SshServer
import java.time.Duration
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.Executors
import java.util.concurrent.ScheduledFuture
import java.util.concurrent.TimeUnit

/** Authenticated idle mounts stay alive; unresponsive peers are still removed. */
class SshSessionPolicy(
    private val interval: Duration = Duration.ofSeconds(30),
    private val replyTimeout: Duration = Duration.ofSeconds(10),
    private val idleTimeout: Duration = Duration.ofMinutes(5),
    private val onUnresponsive: (Session) -> Unit = {}
) : AutoCloseable {
    private val scheduler = Executors.newScheduledThreadPool(2)
    private val heartbeats = ConcurrentHashMap<Session, ScheduledFuture<*>>()

    fun install(server: SshServer) {
        CoreModuleProperties.SOCKET_KEEPALIVE.set(server, true)
        CoreModuleProperties.AUTH_TIMEOUT.set(server, Duration.ofSeconds(30))
        CoreModuleProperties.IDLE_TIMEOUT.set(server, idleTimeout)
        server.addSessionListener(object : SessionListener {
            override fun sessionEvent(session: Session, event: SessionListener.Event) {
                if (event != SessionListener.Event.Authenticated) return
                var misses = 0
                val future = scheduler.scheduleWithFixedDelay({
                    if (!session.isOpen) return@scheduleWithFixedDelay
                    try {
                        // Both SUCCESS and FAILURE are replies proving the peer is alive.
                        val packet = session.createBuffer(SshConstants.SSH_MSG_GLOBAL_REQUEST)
                        packet.putString("keepalive@openssh.com")
                        packet.putBoolean(true)
                        session.request("keepalive@openssh.com", packet, replyTimeout)
                        misses = 0
                    } catch (_: Exception) {
                        misses++
                        if (misses >= 3 && session.isOpen) {
                            onUnresponsive(session)
                            session.close(true)
                        }
                    }
                }, interval.toMillis(), interval.toMillis(), TimeUnit.MILLISECONDS)
                heartbeats.put(session, future)?.cancel(true)
                if (!session.isOpen) heartbeats.remove(session)?.cancel(true)
            }

            override fun sessionClosed(session: Session) {
                heartbeats.remove(session)?.cancel(true)
            }
        })
    }

    override fun close() {
        heartbeats.values.forEach { it.cancel(true) }
        heartbeats.clear()
        scheduler.shutdownNow()
    }
}
