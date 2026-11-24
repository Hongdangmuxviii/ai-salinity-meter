package com.aisalt.meter.analysis

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class SaltGuideTest {
    @Test
    fun patentExampleSalt() {
        // Patent ¶87: 0.9 % -> 1.2 %, 0.8 L -> 2.4 g
        val g = SaltGuide.compute(currentPct = 0.9, targetPct = 1.2, brothMl = 800.0)
        assertEquals(GuideKind.ADD_SALT, g.kind)
        assertEquals(2.4, g.amount!!, 1e-9)
        assertFalse(g.perLiter)
    }

    @Test
    fun patentExampleWater() {
        // Patent ¶90: 1.25 % -> 1.0 %, 0.8 L -> 200 mL
        val g = SaltGuide.compute(currentPct = 1.25, targetPct = 1.0, brothMl = 800.0)
        assertEquals(GuideKind.ADD_WATER, g.kind)
        assertEquals(200.0, g.amount!!, 1e-9)
    }

    @Test
    fun toleranceBand() {
        assertEquals(GuideKind.ON_TARGET, SaltGuide.compute(0.96, 1.0, 800.0).kind)
        assertEquals(GuideKind.ADD_SALT, SaltGuide.compute(0.94, 1.0, 800.0).kind)
    }

    @Test
    fun unknownVolumeGivesPerLiter() {
        val g = SaltGuide.compute(0.5, 0.8, null)
        assertTrue(g.perLiter)
        assertEquals(3.0, g.amount!!, 1e-9)
    }

    @Test
    fun noSalinity() {
        assertEquals(GuideKind.NO_DATA, SaltGuide.compute(null, 0.8, 500.0).kind)
    }

    @Test
    fun sessionAdvisesAfterThreeRounds() {
        val session = AdjustSession(maxRounds = 3)
        val off = SaltGuide.compute(0.5, 0.8, 500.0)
        repeat(3) { session.onRemeasured(off) }
        assertTrue(session.adviseManual)
        session.onRemeasured(SaltGuide.compute(0.8, 0.8, 500.0))
        assertTrue(session.reached)
        assertFalse(session.adviseManual)
    }
}
