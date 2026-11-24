package com.aisalt.meter.analysis

import kotlin.math.PI

/**
 * Container shape -> total food volume from the fill height (patent ¶71-¶73).
 * All lengths in mm, volumes in mL.
 */
sealed interface Container {
    val depthMm: Double

    /** Cross-section area (mm²) at height [hMm] above the floor. */
    fun areaMm2(hMm: Double): Double

    /** Volume (mL) when filled to [fillMm] above the floor. */
    fun volumeMl(fillMm: Double): Double

    /** Round container, straight (top == bottom) or tapered (truncated cone). */
    data class Round(
        val topDiameterMm: Double,
        val bottomDiameterMm: Double,
        override val depthMm: Double,
    ) : Container {
        private fun radiusAt(h: Double): Double {
            val rb = bottomDiameterMm / 2.0
            val rt = topDiameterMm / 2.0
            return if (depthMm > 0) rb + (rt - rb) * (h / depthMm) else rb
        }

        override fun areaMm2(hMm: Double): Double {
            val r = radiusAt(hMm)
            return PI * r * r
        }

        override fun volumeMl(fillMm: Double): Double {
            val h = fillMm.coerceIn(0.0, depthMm)
            val rb = bottomDiameterMm / 2.0
            val rh = radiusAt(h)
            return PI * h * (rb * rb + rb * rh + rh * rh) / 3.0 / 1000.0
        }
    }

    /** Rectangular container: width × length × H. */
    data class Rect(
        val widthMm: Double,
        val lengthMm: Double,
        override val depthMm: Double,
    ) : Container {
        override fun areaMm2(hMm: Double) = widthMm * lengthMm

        override fun volumeMl(fillMm: Double) = widthMm * lengthMm * fillMm.coerceIn(0.0, depthMm) / 1000.0
    }

    /**
     * Container learned with the ToF (method A): known water volumes poured in steps
     * and the fill height measured each time. V(h) is piecewise linear through the
     * points (0, 0), (h1, V1), …; above the last point the last segment's area is
     * extended up to [depthMm].
     */
    data class Calibrated(
        val points: List<CalPoint>,
        override val depthMm: Double,
    ) : Container {
        private val sorted = (listOf(CalPoint(0.0, 0.0)) + points.filter { it.heightMm > 0.0 })
            .sortedBy { it.heightMm }

        init {
            require(sorted.size >= 2) { "need at least one measured point" }
            require(sorted.zipWithNext().all { (a, b) -> b.heightMm > a.heightMm && b.volumeMl >= a.volumeMl }) {
                "heights and volumes must increase together"
            }
        }

        /** Index of the segment containing [h] (the last segment for h above the data). */
        private fun segment(h: Double): Int {
            val i = sorted.indexOfLast { it.heightMm <= h }.coerceAtLeast(0)
            return i.coerceAtMost(sorted.size - 2)
        }

        override fun areaMm2(hMm: Double): Double {
            val i = segment(hMm)
            val a = sorted[i]
            val b = sorted[i + 1]
            return (b.volumeMl - a.volumeMl) * 1000.0 / (b.heightMm - a.heightMm)
        }

        override fun volumeMl(fillMm: Double): Double {
            val h = fillMm.coerceIn(0.0, depthMm)
            val i = segment(h)
            val a = sorted[i]
            return a.volumeMl + areaMm2(h) * (h - a.heightMm) / 1000.0
        }

        val maxCalibratedHeightMm: Double get() = sorted.last().heightMm
    }

    /**
     * Measured or learned area profile A(h) (patent ¶72): V = ∫0..H A(h) dh,
     * integrated with the trapezoid rule. [heightsMm] must be ascending and start at 0.
     */
    data class Profile(
        val heightsMm: List<Double>,
        val areasMm2: List<Double>,
    ) : Container {
        init {
            require(heightsMm.size == areasMm2.size && heightsMm.size >= 2) { "need at least two samples" }
            require(heightsMm.zipWithNext().all { (a, b) -> b > a }) { "heights must ascend" }
        }

        override val depthMm: Double get() = heightsMm.last()

        override fun areaMm2(hMm: Double): Double {
            val h = hMm.coerceIn(heightsMm.first(), heightsMm.last())
            val i = heightsMm.indexOfLast { it <= h }.coerceAtMost(heightsMm.size - 2)
            val t = (h - heightsMm[i]) / (heightsMm[i + 1] - heightsMm[i])
            return areasMm2[i] + t * (areasMm2[i + 1] - areasMm2[i])
        }

        override fun volumeMl(fillMm: Double): Double {
            val h = fillMm.coerceIn(0.0, depthMm)
            var mm3 = 0.0
            for (i in 0 until heightsMm.size - 1) {
                val lo = heightsMm[i]
                if (lo >= h) break
                val hi = minOf(heightsMm[i + 1], h)
                mm3 += (areaMm2(lo) + areaMm2(hi)) / 2.0 * (hi - lo)
            }
            return mm3 / 1000.0
        }
    }
}
