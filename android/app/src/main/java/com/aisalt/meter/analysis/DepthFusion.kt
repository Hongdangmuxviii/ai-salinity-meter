package com.aisalt.meter.analysis

import kotlin.math.abs
import kotlin.math.tan

/**
 * Relative depth map from a monocular model (e.g. Depth Anything / MiDaS), covering the
 * whole photo. Those models output affine-invariant inverse depth (disparity):
 * larger = closer. [isInverse] = false for models that output relative depth instead.
 */
class RelativeDepth(val width: Int, val height: Int, val values: FloatArray, val isInverse: Boolean = true) {
    init {
        require(values.size == width * height) { "depth size mismatch" }
    }

    fun meanIn(rect: NormRect): Double? {
        val x0 = (rect.left * width).toInt().coerceIn(0, width)
        val x1 = (rect.right * width).toInt().coerceIn(0, width)
        val y0 = (rect.top * height).toInt().coerceIn(0, height)
        val y1 = (rect.bottom * height).toInt().coerceIn(0, height)
        var sum = 0.0
        var n = 0
        for (y in y0 until y1) for (x in x0 until x1) {
            val v = values[y * width + x]
            if (v.isFinite()) { sum += v; n++ }
        }
        return if (n == 0) null else sum / n
    }
}

data class DepthFit(
    val scale: Double,
    val offset: Double,
    val zonesUsed: Int,
    val zonesRejected: Int,
    /** Median absolute error of the fitted map against the ToF zones, mm. */
    val medianErrorMm: Double,
)

data class DepthSolidsResult(
    val fit: DepthFit,
    /** Surface distance from broth pixels of the metric map, mm. */
    val surfaceMm: Double,
    /** Solids volume above the surface (before γ), mL. */
    val aboveSurfaceMl: Double,
    val solidPixelsUsed: Int,
)

/**
 * Method C: metric depth map = monocular relative depth scaled by the ToF.
 *  1. mean model value r_i in each valid ToF zone's image rectangle
 *  2. least squares 1/d_i = s·r_i + t (or d_i = s·r_i + t), one outlier-rejection pass
 *  3. per solid pixel: height above the surface × the pixel's floor footprint
 */
object DepthFusion {
    const val MIN_ZONES = 6

    fun fit(
        depth: RelativeDepth,
        tofGrid: IntArray,
        registration: Registration,
        tof: TofGeometry = TofGeometry(),
    ): DepthFit? {
        val n = tof.zonesPerSide
        val xs = ArrayList<Double>()
        val ys = ArrayList<Double>()
        for (row in 0 until n) for (col in 0 until n) {
            val d = tofGrid[row * n + col]
            if (d <= 0) continue
            val r = depth.meanIn(registration.zoneRect(row, col, tof)) ?: continue
            xs += r
            ys += if (depth.isInverse) 1.0 / d else d.toDouble()
        }
        if (xs.size < MIN_ZONES) return null
        var (s, t) = leastSquares(xs, ys) ?: return null
        // One pass of outlier rejection (steam, glare, mixed rim/broth zones).
        val residuals = xs.indices.map { ys[it] - (s * xs[it] + t) }
        val mad = residuals.map { abs(it) }.median() * 1.4826
        val keep = xs.indices.filter { mad == 0.0 || abs(residuals[it]) <= 3.0 * mad }
        if (keep.size >= MIN_ZONES && keep.size < xs.size) {
            leastSquares(keep.map { xs[it] }, keep.map { ys[it] })?.let { (s2, t2) -> s = s2; t = t2 }
        }
        val errors = keep.map { i ->
            val predicted = toMetric(xs[i], s, t, depth.isInverse) ?: return@map Double.MAX_VALUE
            val actual = if (depth.isInverse) 1.0 / ys[i] else ys[i]
            abs(predicted - actual)
        }
        return DepthFit(s, t, keep.size, xs.size - keep.size, errors.median())
    }

    fun toMetric(r: Double, scale: Double, offset: Double, inverse: Boolean): Double? {
        val v = scale * r + offset
        return if (inverse) (if (v > 1e-6) 1.0 / v else null) else (if (v > 0) v else null)
    }

    /**
     * Solids volume above the broth surface from the metric map and the segmentation.
     * The map and the segmentation may have different resolutions; both span the photo.
     */
    fun solidsAboveSurface(
        depth: RelativeDepth,
        fit: DepthFit,
        segmentation: Segmentation,
        registration: Registration,
        marginMm: Double = 3.0,
    ): DepthSolidsResult? {
        val brothDepths = ArrayList<Double>()
        val solid = ArrayList<Double>()
        for (y in 0 until depth.height) for (x in 0 until depth.width) {
            val sx = ((x + 0.5) / depth.width * segmentation.width).toInt().coerceIn(0, segmentation.width - 1)
            val sy = ((y + 0.5) / depth.height * segmentation.height).toInt().coerceIn(0, segmentation.height - 1)
            val label = segmentation.labels[sy * segmentation.width + sx]
            if (label != Segmentation.BROTH && label != Segmentation.SOLID) continue
            val d = toMetric(depth.values[y * depth.width + x].toDouble(), fit.scale, fit.offset, depth.isInverse)
                ?: continue
            if (label == Segmentation.BROTH) brothDepths += d else solid += d
        }
        if (brothDepths.size < 20) return null
        val surface = brothDepths.median()
        // Footprint of one pixel at distance d (pinhole, map spans the camera FoV).
        val kx = 2.0 * tan(Math.toRadians(registration.cameraHFovDeg / 2.0)) / depth.width
        val ky = 2.0 * tan(Math.toRadians(registration.cameraVFovDeg / 2.0)) / depth.height
        var mm3 = 0.0
        for (d in solid) {
            val h = surface - d - marginMm
            if (h > 0) mm3 += h * (d * kx) * (d * ky)
        }
        return DepthSolidsResult(fit, surface, mm3 / 1000.0, solid.size)
    }

    private fun leastSquares(xs: List<Double>, ys: List<Double>): Pair<Double, Double>? {
        val n = xs.size
        val mx = xs.average()
        val my = ys.average()
        var sxx = 0.0
        var sxy = 0.0
        for (i in 0 until n) {
            sxx += (xs[i] - mx) * (xs[i] - mx)
            sxy += (xs[i] - mx) * (ys[i] - my)
        }
        if (sxx < 1e-12) return null  // no depth variation to fit a scale
        val s = sxy / sxx
        return s to (my - s * mx)
    }

    private fun List<Double>.median(): Double {
        if (isEmpty()) return 0.0
        val sorted = sorted()
        return sorted[sorted.size / 2]
    }
}
