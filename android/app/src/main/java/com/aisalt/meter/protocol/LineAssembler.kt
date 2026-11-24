package com.aisalt.meter.protocol

import java.io.ByteArrayOutputStream

/** Joins NUS TX notifications (split at the MTU) back into '\n'-terminated lines. */
class LineAssembler(private val maxLineBytes: Int = 8192) {
    private val buffer = ByteArrayOutputStream()

    fun feed(bytes: ByteArray): List<String> {
        val lines = mutableListOf<String>()
        for (b in bytes) {
            if (b == '\n'.code.toByte()) {
                if (buffer.size() > 0) lines += buffer.toString(Charsets.UTF_8.name()).trimEnd('\r')
                buffer.reset()
            } else if (buffer.size() < maxLineBytes) {
                buffer.write(b.toInt())
            }
        }
        return lines
    }

    fun reset() = buffer.reset()
}
