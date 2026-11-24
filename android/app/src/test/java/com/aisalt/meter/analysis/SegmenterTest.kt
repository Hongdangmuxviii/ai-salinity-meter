package com.aisalt.meter.analysis

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class SegmenterTest {
    private fun argb(r: Int, g: Int, b: Int) = (0xFF shl 24) or (r shl 16) or (g shl 8) or b

    @Test
    fun redBlockInBrownBroth() {
        val w = 200
        val h = 200
        val broth = argb(170, 110, 60)
        val solid = argb(40, 140, 40)
        val px = IntArray(w * h) { broth }
        // 40×40 green block near the centre (inside the opening circle).
        for (y in 80 until 120) for (x in 60 until 100) px[y * w + x] = solid
        val seg = ColorSolidsSegmenter().segment(RgbImage(w, h, px), BowlCircle(0.5, 0.5, 0.45))
        val opening = Math.PI * (0.45 * 200 * 0.9).let { it * it }
        val expected = 1600.0 / opening
        assertEquals(expected, seg.alpha, 0.01)
    }

    @Test
    fun glareIsExcluded() {
        val w = 100
        val h = 100
        val px = IntArray(w * h) { argb(170, 110, 60) }
        for (y in 45 until 55) for (x in 45 until 55) px[y * w + x] = argb(255, 255, 255)
        val seg = ColorSolidsSegmenter().segment(RgbImage(w, h, px), BowlCircle())
        assertEquals(0.0, seg.alpha, 1e-9)
        assertTrue(seg.glarePixels > 50)
    }

    @Test
    fun labOfWhiteAndBlack() {
        assertEquals(100.0, Lab.fromArgb(argb(255, 255, 255)).l, 0.1)
        assertEquals(0.0, Lab.fromArgb(argb(0, 0, 0)).l, 0.1)
    }
}
