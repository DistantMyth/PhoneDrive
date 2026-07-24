package com.phonedrive.sftp

import org.apache.sshd.common.file.virtualfs.VirtualFileSystemFactory
import org.apache.sshd.common.session.SessionContext
import java.nio.file.FileSystem
import java.nio.file.Path
import java.nio.file.Paths

class AndroidFileSystemFactory(private val rootPath: String) : VirtualFileSystemFactory() {
    init {
        val rootPathObj = Paths.get(rootPath)
        defaultHomeDir = rootPathObj
    }

    override fun createFileSystem(session: SessionContext?): FileSystem {
        return super.createFileSystem(session)
    }

    override fun computeRootDir(session: SessionContext?): Path {
        return Paths.get(rootPath)
    }
}
