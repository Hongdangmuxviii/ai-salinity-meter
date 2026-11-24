package com.aisalt.meter.protocol

import java.util.zip.CRC32

/**
 * Rebuilds a JPEG from IMG notifications: [u16 imageId LE][u16 chunkIndex LE][payload].
 * Chunks may arrive before image_begin is parsed, so early packets are held briefly.
 */
class ImageAssembler {
    data class Progress(val id: Int, val received: Int, val total: Int)

    private var meta: DeviceEvent.ImageBegin? = null
    private var data = ByteArray(0)
    private var have = BooleanArray(0)
    private var count = 0
    private val early = ArrayDeque<ByteArray>()

    val current: DeviceEvent.ImageBegin? get() = meta

    fun begin(event: DeviceEvent.ImageBegin) {
        meta = event
        data = ByteArray(event.bytes)
        have = BooleanArray(event.chunks)
        count = 0
        val pending = early.toList()
        early.clear()
        pending.forEach { accept(it) }
    }

    /** Returns true when the packet belonged to the current image. */
    fun accept(packet: ByteArray): Boolean {
        if (packet.size < 4) return false
        val id = (packet[0].toInt() and 0xFF) or ((packet[1].toInt() and 0xFF) shl 8)
        val index = (packet[2].toInt() and 0xFF) or ((packet[3].toInt() and 0xFF) shl 8)
        val m = meta
        if (m == null || (m.id and 0xFFFF) != id) {
            if (early.size < 64) early.addLast(packet)
            return false
        }
        if (index >= have.size) return false
        val offset = index * m.chunkBytes
        val length = minOf(packet.size - 4, data.size - offset)
        if (length <= 0) return false
        System.arraycopy(packet, 4, data, offset, length)
        if (!have[index]) {
            have[index] = true
            count++
        }
        return true
    }

    fun progress(): Progress? = meta?.let { Progress(it.id, count, it.chunks) }

    fun missing(): List<Int> = have.indices.filter { !have[it] }

    val isComplete: Boolean get() = meta != null && count == have.size

    /** The JPEG when complete and the CRC-32 matches, otherwise null. */
    fun result(): ByteArray? {
        val m = meta ?: return null
        if (!isComplete) return null
        val crc = CRC32().apply { update(data) }.value
        return if (m.crc32 < 0 || crc == m.crc32) data.copyOf() else null
    }

    fun crcMatches(): Boolean? {
        val m = meta ?: return null
        if (!isComplete) return null
        return CRC32().apply { update(data) }.value == m.crc32
    }
}
