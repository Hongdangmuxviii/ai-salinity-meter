package com.aisalt.meter.protocol

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.zip.CRC32

class ProtocolTest {
    @Test
    fun linesSplitAcrossNotifications() {
        val a = LineAssembler()
        assertTrue(a.feed("{\"type\":\"ack\",".toByteArray()).isEmpty())
        val lines = a.feed("\"cmd\":\"time\"}\n{\"type\":\"temp\",\"tempC\":20.5}\n".toByteArray())
        assertEquals(2, lines.size)
        assertEquals(DeviceEvent.Ack("time"), DeviceEvent.parse(lines[0]))
        assertEquals(20.5, (DeviceEvent.parse(lines[1]) as DeviceEvent.Temp).tempC!!, 1e-9)
    }

    @Test
    fun salinityWithNulls() {
        val e = DeviceEvent.parse(
            """{"type":"salinity","seq":7,"pct":null,"tablePct":null,"index":101.2,"tempC":20.1,""" +
                """"span":"OUTSIDE_MODEL_DOMAIN","trials":[101.1,101.2,101.3],"unstable":false}""",
        ) as DeviceEvent.Salinity
        assertNull(e.pct)
        assertEquals(3, e.trials.size)
        assertEquals("OUTSIDE_MODEL_DOMAIN", e.span)
    }

    @Test
    fun tofGrid() {
        val grid = (0 until 64).joinToString(",") { if (it == 5) "-1" else "150" }
        val e = DeviceEvent.parse("""{"type":"tof","surfaceMm":150.0,"grid":[$grid]}""") as DeviceEvent.Tof
        assertEquals(64, e.grid.size)
        assertEquals(-1, e.grid[5])
    }

    @Test
    fun imageReassemblyWithResend() {
        val jpeg = ByteArray(1000) { (it * 7).toByte() }
        val crc = CRC32().apply { update(jpeg) }.value
        val chunkBytes = 240
        val chunks = (jpeg.size + chunkBytes - 1) / chunkBytes
        val asm = ImageAssembler()
        asm.begin(DeviceEvent.ImageBegin(3, jpeg.size, crc, 640, 480, chunkBytes, chunks))
        fun packet(i: Int): ByteArray {
            val start = i * chunkBytes
            val end = minOf(jpeg.size, start + chunkBytes)
            return byteArrayOf(3, 0, i.toByte(), 0) + jpeg.copyOfRange(start, end)
        }
        (0 until chunks).filter { it != 2 }.forEach { asm.accept(packet(it)) }
        assertEquals(listOf(2), asm.missing())
        assertEquals(listOf("img 3 2"), Commands.resendChunks(3, asm.missing()))
        asm.accept(packet(2))
        assertArrayEquals(jpeg, asm.result())
    }

    @Test
    fun packetsBeforeBeginAreKept() {
        val data = ByteArray(10) { it.toByte() }
        val asm = ImageAssembler()
        asm.accept(byteArrayOf(9, 0, 0, 0) + data)
        asm.begin(DeviceEvent.ImageBegin(9, 10, CRC32().apply { update(data) }.value, null, null, 16, 1))
        assertArrayEquals(data, asm.result())
    }
}
