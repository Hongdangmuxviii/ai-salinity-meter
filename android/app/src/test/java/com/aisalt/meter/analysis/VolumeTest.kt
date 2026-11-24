package com.aisalt.meter.analysis

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.PI

class VolumeTest {
    @Test
    fun cylinder() {
        val c = Container.Round(100.0, 100.0, 80.0)
        assertEquals(PI * 50 * 50 * 50 / 1000.0, c.volumeMl(50.0), 1e-9)
    }

    @Test
    fun frustumMatchesProfileIntegral() {
        val round = Container.Round(topDiameterMm = 120.0, bottomDiameterMm = 80.0, depthMm = 60.0)
        val heights = (0..60).map { it.toDouble() }
        val profile = Container.Profile(heights, heights.map { round.areaMm2(it) })
        assertEquals(round.volumeMl(45.0), profile.volumeMl(45.0), 0.5)
    }

    @Test
    fun rect() {
        assertEquals(200.0 * 100.0 * 30.0 / 1000.0, Container.Rect(200.0, 100.0, 50.0).volumeMl(30.0), 1e-9)
    }

    @Test
    fun zoneFootprint() {
        // 45°/8 per zone: side = 2·d·tan(2.8125°) ≈ 0.0982·d
        val side = Math.sqrt(TofGeometry().zoneAreaMm2(200.0))
        assertEquals(19.65, side, 0.05)
    }

    private fun flatGrid(distance: Int) = IntArray(64) { distance }

    @Test
    fun brothWithoutImage() {
        val est = BrothEstimator.estimate(
            BrothInputs(
                tofGrid = flatGrid(150),
                floorMm = 200.0,
                container = Container.Round(100.0, 100.0, 80.0),
                segmentation = null,
            ),
        )
        assertEquals(150.0, est.surfaceMm!!, 1e-9)
        assertEquals(50.0, est.fillMm!!, 1e-9)
        assertEquals(PI * 50 * 50 * 50 / 1000.0, est.totalMl!!, 1e-6)
        assertEquals(est.totalMl!!, est.brothMl!!, 1e-9)
        assertTrue(est.notes.any { it.contains("no image") })
    }

    @Test
    fun noFloorNoVolume() {
        val est = BrothEstimator.estimate(
            BrothInputs(flatGrid(150), null, Container.Round(100.0, 100.0, 80.0), null),
        )
        assertNotNull(est.surfaceMm)
        assertNull(est.totalMl)
    }

    @Test
    fun areaMethodSubtractsSolids() {
        // Synthetic segmentation: right half of the image is solid.
        val w = 80
        val h = 60
        val labels = ByteArray(w * h) { i -> if (i % w >= w / 2) Segmentation.SOLID else Segmentation.BROTH }
        val seg = Segmentation(w, h, labels, Lab(50.0, 0.0, 0.0), w * h / 2, w * h / 2, 0, "test")
        val est = BrothEstimator.estimate(
            BrothInputs(
                tofGrid = flatGrid(150),
                floorMm = 200.0,
                container = Container.Round(100.0, 100.0, 80.0),
                segmentation = seg,
                solids = SolidsModel(method = SolidsMethod.AREA, gammaArea = 0.5),
            ),
        )
        val total = est.totalMl!!
        assertEquals(0.5, est.alpha!!, 1e-9)
        assertEquals(total * 0.5 * 0.5, est.solidsMl!!, 1e-6)
        assertEquals(total * 0.75, est.brothMl!!, 1e-6)
    }

    @Test
    fun protrusionCountsRaisedSolidZones() {
        val w = 80
        val h = 60
        val labels = ByteArray(w * h) { Segmentation.BROTH }
        val reg = Registration()
        val tof = TofGeometry()
        // Mark the image area of zone (3,3) as solid and raise that zone by 20 mm.
        val rect = reg.zoneRect(3, 3, tof)
        for (y in (rect.top * h).toInt() until (rect.bottom * h).toInt())
            for (x in (rect.left * w).toInt() until (rect.right * w).toInt()) labels[y * w + x] = Segmentation.SOLID
        val seg = Segmentation(w, h, labels, Lab(50.0, 0.0, 0.0), 1, 1, 0, "test")
        val grid = flatGrid(150).also { it[3 * 8 + 3] = 130 }
        val est = BrothEstimator.estimate(
            BrothInputs(
                grid, 200.0, Container.Round(100.0, 100.0, 80.0), seg, reg, tof,
                SolidsModel(method = SolidsMethod.PROTRUSION, gammaProtrusion = 1.0, protrusionMarginMm = 0.0),
            ),
        )
        assertEquals(150.0, est.surfaceMm!!, 1e-9)
        val expected = 20.0 * tof.zoneAreaMm2(130.0) / 1000.0
        assertEquals(expected, est.solidsProtrusionMl!!, 1e-6)
        assertEquals(1, est.solidZones)
    }
}
