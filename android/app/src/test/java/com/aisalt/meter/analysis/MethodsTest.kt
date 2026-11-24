package com.aisalt.meter.analysis

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.PI
import kotlin.math.tan

/** Methods A–D (container learning, displacement, depth-map fusion, back-calculation). */
class MethodsTest {
    private val cylinderArea = PI * 50.0 * 50.0  // Ø100 mm, mm²

    // ---------------------------------------------------------------- A

    @Test
    fun containerLearningReproducesCylinder() {
        val floor = 200.0
        val learning = ContainerLearning(floor, depthMm = 90.0)
        var poured = 0.0
        repeat(3) {
            poured += 200.0
            val h = poured * 1000.0 / cylinderArea
            val r = learning.addStep(200.0, floor - h)
            assertTrue(r is ContainerLearning.StepResult.Added)
        }
        val c = learning.profile("cyl")!!.container()
        assertEquals(cylinderArea * 40.0 / 1000.0, c.volumeMl(40.0), 0.01)
        // Above the last learned point the last segment's area is extended.
        assertEquals(cylinderArea * 85.0 / 1000.0, c.volumeMl(85.0), 0.01)
        assertEquals(100.0, learning.lastEquivalentDiameterMm()!!, 0.01)
    }

    @Test
    fun containerLearningRejectsNoRise() {
        val learning = ContainerLearning(200.0, 90.0)
        learning.addStep(100.0, 180.0)
        assertTrue(learning.addStep(100.0, 180.2) is ContainerLearning.StepResult.Rejected)
        assertEquals(1, learning.points.size)
    }

    // ---------------------------------------------------------------- B

    @Test
    fun displacementOfAddedSolids() {
        val c = Container.Round(100.0, 100.0, 90.0)
        val ledger = DisplacementLedger()
        ledger.markBefore(c, 30.0)
        val entry = ledger.markAfter(c, 40.0, "두부", null, 0)!!
        assertEquals(cylinderArea * 10.0 / 1000.0, entry.displacedMl, 1e-9)
        assertEquals(cylinderArea * 30.0 / 1000.0, ledger.initialLiquidMl!!, 1e-9)
        assertNull(ledger.markAfter(c, 45.0, "x", null, 0))  // needs a new "before"
    }

    // ---------------------------------------------------------------- C

    @Test
    fun depthFusionRecoversScaleAndSolids() {
        val w = 160
        val h = 120
        val reg = Registration()
        val tof = TofGeometry()
        // Scene: table 250 mm, bowl opening (circle) broth at 150 mm, a block at 130 mm.
        val metric = DoubleArray(w * h)
        val labels = ByteArray(w * h)
        val cx = w / 2.0
        val cy = h / 2.0
        val r = 0.42 * h
        var solidPixels = 0
        for (y in 0 until h) for (x in 0 until w) {
            val i = y * w + x
            val inside = (x + 0.5 - cx) * (x + 0.5 - cx) + (y + 0.5 - cy) * (y + 0.5 - cy) <= r * r
            val block = x in 70 until 90 && y in 50 until 70
            metric[i] = when {
                block -> 130.0
                inside -> 150.0
                else -> 250.0
            }
            labels[i] = when {
                block -> { solidPixels++; Segmentation.SOLID }
                inside -> Segmentation.BROTH
                else -> Segmentation.OUTSIDE
            }
        }
        val s = 0.004
        val t = 0.002
        val rel = FloatArray(w * h) { ((1.0 / metric[it] - t) / s).toFloat() }
        val depth = RelativeDepth(w, h, rel)
        // ToF zone distance consistent with the mean inverse depth over its footprint.
        val grid = IntArray(64) { z ->
            val mean = depth.meanIn(reg.zoneRect(z / 8, z % 8, tof))!!
            (1.0 / (s * mean + t)).let { Math.round(it).toInt() }
        }
        val fit = DepthFusion.fit(depth, grid, reg, tof)!!
        assertTrue("median error ${fit.medianErrorMm}", fit.medianErrorMm < 1.0)

        val seg = Segmentation(w, h, labels, Lab(50.0, 0.0, 0.0), 1, 1, 0, "test")
        val result = DepthFusion.solidsAboveSurface(depth, fit, seg, reg, marginMm = 0.0)!!
        assertEquals(150.0, result.surfaceMm, 1.0)
        val kx = 2.0 * tan(Math.toRadians(reg.cameraHFovDeg / 2)) / w
        val ky = 2.0 * tan(Math.toRadians(reg.cameraVFovDeg / 2)) / h
        val expected = solidPixels * 20.0 * (130.0 * kx) * (130.0 * ky) / 1000.0
        assertEquals(expected, result.aboveSurfaceMl, expected * 0.1)
    }

    @Test
    fun depthFusionNeedsVariation() {
        val depth = RelativeDepth(80, 60, FloatArray(80 * 60) { 1f })
        assertNull(DepthFusion.fit(depth, IntArray(64) { 150 }, Registration()))
    }

    // ---------------------------------------------------------------- D

    @Test
    fun saltBackCalculationMatchesPatentExample() {
        val e = BackCalc.brothAfter(AdditionRecord("SALT", 2.4, 0.9, 1.2))!!
        assertEquals(800.0, e.valueMl, 1e-6)
        assertTrue(e.relSigma in 0.08..0.12)
    }

    @Test
    fun waterBackCalculation() {
        // 800 mL at 1.25 % + 200 mL water -> 1.0 %
        val e = BackCalc.brothAfter(AdditionRecord("WATER", 200.0, 1.25, 1.0))!!
        assertEquals(1000.0, e.valueMl, 1e-6)
    }

    @Test
    fun tooSmallChangeIsRejected() {
        assertNull(BackCalc.brothAfter(AdditionRecord("SALT", 0.3, 0.90, 0.94)))
    }

    @Test
    fun fusionWeightsByUncertainty() {
        val f = Fusion.combine(listOf(Estimate(1000.0, 0.10, "a"), Estimate(800.0, 0.05, "b")))!!
        // weights 1/100² and 1/40² -> closer to 800
        assertTrue(f.valueMl in 800.0..850.0)
        assertTrue(f.sigmaMl < 40.0)
    }

    @Test
    fun foodCorrectionLearnsRatio() {
        var c = FoodCorrection("라면")
        repeat(3) { c = c.observe(Estimate(800.0, 0.1, "salt"), Estimate(1000.0, 0.2, "cam")) }
        assertEquals(0.8, c.factor, 1e-9)
        assertEquals(3, c.count)
    }

    @Test
    fun plannerPrefersDisplacementAndSplitsFirstAddition() {
        val plan = VolumePlanner.plan(
            total = 1000.0, calibratedContainer = true,
            displacementMl = 200.0, depthSolidsMl = 300.0, areaSolidsMl = 400.0, tofSolidsMl = null,
            correction = null, backCalc = null,
        )
        assertEquals(SolidsSource.DISPLACEMENT, plan.solidsSource)
        assertEquals(800.0, plan.final!!.valueMl, 1e-9)
        assertTrue(plan.firstStepRatio < 1.0 && plan.firstStepRatio >= 0.5)

        val withBack = VolumePlanner.plan(
            1000.0, true, 200.0, null, null, null, null, Estimate(700.0, 0.05, "salt"),
        )
        assertEquals(1.0, withBack.firstStepRatio, 1e-9)
        assertNotNull(withBack.final)
        assertTrue(withBack.final!!.valueMl in 700.0..800.0)
    }
}
