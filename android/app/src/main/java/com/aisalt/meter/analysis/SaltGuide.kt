package com.aisalt.meter.analysis

import kotlin.math.abs

enum class GuideKind { NO_DATA, ADD_SALT, ADD_WATER, ON_TARGET }

data class Guide(
    val kind: GuideKind,
    /** g of salt or mL of water; per 1 L of broth when [perLiter]. */
    val amount: Double?,
    val perLiter: Boolean,
    val deltaPct: Double?,
) {
    val unit: String get() = if (kind == GuideKind.ADD_WATER) "mL" else "g"
}

/** Patent S500-S600, equations 1 and 2. */
object SaltGuide {
    /** g of NaCl that raises 1 L by 1 %p (patent ¶86). */
    const val K_DEFAULT = 10.0
    /** S700 completion band, ±%p (patent ¶99). */
    const val TOLERANCE_PCT = 0.05

    fun compute(
        currentPct: Double?,
        targetPct: Double,
        brothMl: Double?,
        k: Double = K_DEFAULT,
        tolerance: Double = TOLERANCE_PCT,
    ): Guide {
        if (currentPct == null || currentPct.isNaN() || targetPct <= 0.0) {
            return Guide(GuideKind.NO_DATA, null, false, null)
        }
        val delta = targetPct - currentPct
        if (abs(delta) <= tolerance) return Guide(GuideKind.ON_TARGET, 0.0, false, delta)
        val perLiter = brothMl == null || brothMl <= 0.0
        val liters = if (perLiter) 1.0 else brothMl!! / 1000.0
        return if (delta > 0) {
            // Eq.1: Wsalt = (Starget − Scurrent) × Vbroth[L] × K
            Guide(GuideKind.ADD_SALT, delta * liters * k, perLiter, delta)
        } else {
            // Eq.2: Vwater = Vbroth × (Scurrent / Starget − 1)
            Guide(GuideKind.ADD_WATER, liters * (currentPct / targetPct - 1.0) * 1000.0, perLiter, delta)
        }
    }
}

/** S700 add → mix → re-measure loop. */
class AdjustSession(private val maxRounds: Int = 3) {
    var rounds: Int = 0
        private set
    var reached: Boolean = false
        private set
    val adviseManual: Boolean get() = !reached && rounds >= maxRounds

    fun reset() {
        rounds = 0
        reached = false
    }

    /** Call after each re-measurement that followed an addition. */
    fun onRemeasured(guide: Guide) {
        rounds++
        reached = guide.kind == GuideKind.ON_TARGET
    }

    fun onFirstMeasurement(guide: Guide) {
        reset()
        reached = guide.kind == GuideKind.ON_TARGET
    }
}
