package com.aisalt.meter.analysis

import kotlinx.serialization.Serializable

/** One container-learning sample: fill height above the floor and the water poured so far. */
@Serializable
data class CalPoint(val heightMm: Double, val volumeMl: Double)

/** A learned container, stored by name (method A). */
@Serializable
data class ContainerProfile(
    val name: String,
    val floorMm: Double,
    val depthMm: Double,
    val points: List<CalPoint>,
) {
    fun container(): Container.Calibrated = Container.Calibrated(points, depthMm)
}

/**
 * Method A, patent ¶72 ("define or learn A(h)"): the empty container's floor distance
 * is measured first, then known water volumes are poured in steps and the surface is
 * measured with the ToF after each step.
 */
class ContainerLearning(val floorMm: Double, val depthMm: Double) {
    private val _points = mutableListOf<CalPoint>()
    val points: List<CalPoint> get() = _points
    val totalMl: Double get() = _points.lastOrNull()?.volumeMl ?: 0.0

    sealed interface StepResult {
        data class Added(val point: CalPoint, val segmentAreaMm2: Double) : StepResult
        data class Rejected(val reason: String) : StepResult
    }

    /**
     * Records that [pouredMl] more water was added and the surface is now at
     * [surfaceMm] from the sensor.
     */
    fun addStep(pouredMl: Double, surfaceMm: Double): StepResult {
        if (pouredMl <= 0.0) return StepResult.Rejected("poured volume must be positive")
        val h = floorMm - surfaceMm
        val previous = _points.lastOrNull() ?: CalPoint(0.0, 0.0)
        if (h <= previous.heightMm + 0.5) {
            return StepResult.Rejected(
                "surface did not rise (h=%.1f mm, previous %.1f mm)".format(h, previous.heightMm),
            )
        }
        if (h > depthMm * 1.05) return StepResult.Rejected("height exceeds the container depth")
        val point = CalPoint(h, previous.volumeMl + pouredMl)
        _points += point
        val area = (point.volumeMl - previous.volumeMl) * 1000.0 / (point.heightMm - previous.heightMm)
        return StepResult.Added(point, area)
    }

    fun undo() {
        if (_points.isNotEmpty()) _points.removeAt(_points.lastIndex)
    }

    fun profile(name: String): ContainerProfile? =
        if (_points.isEmpty()) null else ContainerProfile(name, floorMm, depthMm, _points.toList())

    /** Equivalent diameter of the last segment, for a plausibility check in the UI. */
    fun lastEquivalentDiameterMm(): Double? {
        if (_points.isEmpty()) return null
        val prev = if (_points.size >= 2) _points[_points.size - 2] else CalPoint(0.0, 0.0)
        val last = _points.last()
        val area = (last.volumeMl - prev.volumeMl) * 1000.0 / (last.heightMm - prev.heightMm)
        return 2.0 * kotlin.math.sqrt(area / Math.PI)
    }
}
