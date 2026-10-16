package com.phonedrive.sftp

import org.apache.sshd.client.SshClient
import org.apache.sshd.common.keyprovider.KeyPairProvider
import org.apache.sshd.server.SshServer
import org.apache.sshd.core.CoreModuleProperties
import org.junit.Assert.*
import org.junit.Test
import java.security.KeyPairGenerator
import java.time.Duration

class SshSessionPolicyTest {
    @Test fun idleAuthenticatedConnectionSurvivesAndAuthenticationStillExpires() {
        val keys = KeyPairGenerator.getInstance("RSA").apply { initialize(2048) }.generateKeyPair()
        val server = SshServer.setUpDefaultServer().apply {
            host = "127.0.0.1"
            port = 0
            keyPairProvider = KeyPairProvider.wrap(keys)
            passwordAuthenticator = org.apache.sshd.server.auth.password.PasswordAuthenticator { u, p, _ -> u == "phone" && p == "test-password" }
        }
        val policy = SshSessionPolicy(Duration.ofMillis(100), Duration.ofMillis(300), Duration.ofSeconds(2))
        policy.install(server)
        assertEquals(Duration.ofSeconds(30), CoreModuleProperties.AUTH_TIMEOUT.getRequired(server))
        assertTrue(CoreModuleProperties.SOCKET_KEEPALIVE.getRequired(server))
        server.start()
        try {
            SshClient.setUpDefaultClient().use { client ->
                client.start()
                client.connect("phone", "127.0.0.1", server.port).verify(5000).session.use { session ->
                    session.addPasswordIdentity("test-password")
                    session.auth().verify(5000)
                    Thread.sleep(3_000)
                    assertTrue("Heartbeats must keep an idle authenticated mount alive", session.isOpen)
                }
            }
        } finally {
            policy.close()
            server.stop(true)
        }
    }
}
