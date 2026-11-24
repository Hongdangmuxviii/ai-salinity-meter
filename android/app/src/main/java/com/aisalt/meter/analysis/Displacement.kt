package com.aisalt.meter.analysis

import kotlinx.serialization.Serializable

/**
 * Method B: solids volume from the surface rise when they are added. The ToF sees
 * the rise even for solids hidden under the surface, which the camera cannot see.
 */
@Serializable
data class SolidsAddition(
    val label: String,
    val heightBeforeMm: Double,
    val heightAfterMm: Double,
    val displacedMl: Double,
    /** Solids area ratio α in the photo taken after adding, if any. */
    val alphaAfter: Double? = null,
    val timeMillis: Long = 0,
)

class DisplacementLedger {
    private val _additions = mutableListOf<SolidsAddition>()
    val additions: List<SolidsAddition> get() = _additions

    /** Water/broth volume measured before the first solids went in (the pre-cooking amount). */
    var initialLiquidMl: Double? = null
        private set

    private var pendingBefore: Double? = null
    val waitingForAfter: Boolean get() = pendingBefore != null

    val totalSolidsMl: Double get() = _additions.sumOf { it.displacedMl }

    fun clear() {
        _additions.clear()
        initialLiquidMl = null
        pendingBefore = null
    }

    /** Fill height measured just before the solids are added. */
    fun markBefore(container: Container, heightMm: Double) {
        pendingBefore = heightMm
        if (_additions.isEmpty() && initialLiquidMl == null) initialLiquidMl = container.volumeMl(heightMm)
    }

    /** Fill height measured right after adding; returns the new ledger entry. */
    fun markAfter(
        container: Container,
        heightMm: Double,
        label: String,
        alphaAfter: Double?,
        timeMillis: Long,
    ): SolidsAddition? {
        val before = pendingBefore ?: return null
        pendingBefore = null
        val displaced = (container.volumeMl(heightMm) - container.volumeMl(before)).coerceAtLeast(0.0)
        val entry = SolidsAddition(label, before, heightMm, displaced, alphaAfter, timeMillis)
        _additions += entry
        return entry
    }

    fun restore(initial: Double?, items: List<SolidsAddition>) {
        clear()
        initialLiquidMl = initial
        _additions += items
    }
}
