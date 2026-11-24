package com.aisalt.meter.analysis

import kotlin.math.tan

/** Rectangle in normalised image coordinates (0..1, origin top-left). */
data class NormRect(val left: Double, val top: Double, val right: Double, val bottom: Double) {
    val isEmpty: Boolean get() = right <= left || bottom <= top
}

/**
 * VL53L5CX 8×8 multizone ToF. The sensor's field of view is 45° per axis
 * (63° diagonal), split evenly into zones.
 */
data class TofGeometry(
    val fovDeg: Double = 45.0,
    val zonesPerSide: Int = 8,
) {
    /** Floor footprint (mm²) of one zone at [distanceMm] (small-angle square approximation). */
    fun zoneAreaMm2(distanceMm: Double): Double {
        val half = Math.toRadians(fovDeg / zonesPerSide / 2.0)
        val side = 2.0 * distanceMm * tan(half)
        return side * side
    }

    /** Angular span (deg, from the optical axis) of zone index [i] along one axis. */
    fun zoneAnglesDeg(i: Int): Pair<Double, Double> {
        val step = fovDeg / zonesPerSide
        val start = -fovDeg / 2.0 + i * step
        return start to start + step
    }
}

/**
 * Camera ↔ ToF coordinate registration (patent ¶60-¶61).
 *
 * MVP model: both sensors look straight down from nearly the same point, so a ToF
 * zone maps to an image rectangle through the two fields of view. Mounting
 * rotation / mirroring and a residual offset are parameters; a checkerboard
 * extrinsic calibration can replace this later.
 *
 * Camera FoV defaults are for the XIAO ESP32-S3 Sense OV2640 lens and must be
 * confirmed on the real module (OV3660 units differ).
 */
data class Registration(
    val cameraHFovDeg: Double = 55.0,
    val cameraVFovDeg: Double = 42.0,
    val rotateQuarterTurns: Int = 0,
    val mirrorX: Boolean = false,
    val offsetX: Double = 0.0,
    val offsetY: Double = 0.0,
) {
    fun zoneRect(row: Int, col: Int, tof: TofGeometry): NormRect {
        val n = tof.zonesPerSide
        var r = row
        var c = col
        repeat(((rotateQuarterTurns % 4) + 4) % 4) {
            val nr = c
            val nc = n - 1 - r
            r = nr
            c = nc
        }
        if (mirrorX) c = n - 1 - c
        val (x0, x1) = tof.zoneAnglesDeg(c)
        val (y0, y1) = tof.zoneAnglesDeg(r)
        val hx = tan(Math.toRadians(cameraHFovDeg / 2.0))
        val hy = tan(Math.toRadians(cameraVFovDeg / 2.0))
        fun mapX(deg: Double) = 0.5 + tan(Math.toRadians(deg)) / (2.0 * hx) + offsetX
        fun mapY(deg: Double) = 0.5 + tan(Math.toRadians(deg)) / (2.0 * hy) + offsetY
        return NormRect(
            mapX(x0).coerceIn(0.0, 1.0), mapY(y0).coerceIn(0.0, 1.0),
            mapX(x1).coerceIn(0.0, 1.0), mapY(y1).coerceIn(0.0, 1.0),
        )
    }
}
